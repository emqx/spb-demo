import os
import logging
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from llama_index.llms.siliconflow import SiliconFlow
from llama_index.llms.deepseek import DeepSeek
from sse_starlette.sse import EventSourceResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json

from demo_flow import DemoFlow, Context, ProgressEvent
from session_store import SessionStore
from db.rag import RAG

project_path = os.path.abspath(os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO, filename=os.path.join(project_path, "logs/mcp_service.log"), filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

app = FastAPI()
session_store = SessionStore()

# Add after creating the FastAPI app
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("index.html")

llm = SiliconFlow(
    api_key=os.getenv("SFAPI_KEY"),
    model=str(os.getenv("MODEL_NAME")),
    temperature=0.6,
    max_tokens=4000,
    timeout=180
)

rag = RAG()
try:
    rag.load_index_from_docx()
except Exception as e:
    rag.create_from_docx()

# llm = DeepSeek(model=os.getenv("DS_MODEL_NAME"), api_key=os.getenv("DS_API_KEY"),temperature=0.6,max_tokens=6000)

async def event_generator(prompt: str, session_id: str):
    # Get existing memory or create new one
    memory = session_store.get_memory(session_id)
    if memory is not None:
        print(memory.get())

    device_info = '''要查询的设备是 ABB FlexPendant。ABB FlexPendant 是一款手持式触摸屏设备，用于编程和控制 ABB 工业机器人。它作为机器人控制器的用户界面，允许操作员执行多种操作，如更改和运行程序、教授机器人新的动作以及调整参数。
          
          设备定义的点位如下所示，
          ```json
          {
            "robotic_arm": { "voltage": 3.14, "amper": 5.0},
            "diagnose": {"error_code": 50153}
          }
        其中 robotic_arm 分组中包含了 voltage 和 amper 数据；
        其中 diagnose 分组中包含了 error_code 是设备上报的错误代码；
          '''
    # Initialize the LLM and workflow
    workflow = DemoFlow(timeout=None, llm=llm, rag=rag, verbose=True, memory=memory)
    ctx = Context(workflow)

    # Run the workflow
    handler = workflow.run(user_input=prompt, device_info=device_info, ctx=ctx)

    try:
        async for ev in handler.stream_events():
            if isinstance(ev, ProgressEvent):
                # Yield SSE formatted data
                # print(ev.msg, end="", flush=True)
                yield {
                    "event": "message",
                    "data": f'{json.dumps({"content": ev.msg})}\n\n'
                }
    except Exception as e:
        yield {
            "event": "error",
            "data": str(e)
        }
    finally:
        # Save the updated memory
        session_store.save_memory(session_id, workflow.memory)

@app.post("/stream")
async def stream_llm_response(request: Request):
    # Get the prompt from the request body
    data = await request.json()
    user_prompt = data.get("prompt", "")
    
    # Get session ID from header, or generate new one if not present
    session_id = request.headers.get("X-Tab-Session")
    if not session_id:
        session_id = str(uuid.uuid4())
    
    return EventSourceResponse(
        event_generator(user_prompt, session_id),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
