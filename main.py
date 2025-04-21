import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from llama_index.llms.siliconflow import SiliconFlow
from sse_starlette.sse import EventSourceResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json

from demo_flow import DemoFlow, Context, ProgressEvent

project_path = os.path.abspath(os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO, filename=os.path.join(project_path, "logs/mcp_service.log"), filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

app = FastAPI()

# Add after creating the FastAPI app
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("index.html")

llm = SiliconFlow(
    api_key=os.getenv("SFAPI_KEY"),
    model=os.getenv("MODEL_NAME"),
    temperature=0.6,
    max_tokens=4000,
    timeout=180
)

async def event_generator(prompt: str):
    # Initialize the LLM and workflow
    workflow = DemoFlow(timeout=None, llm=llm, verbose=False)
    ctx = Context(workflow)

    # Run the workflow
    handler = workflow.run(user_input=prompt, ctx=ctx)

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

@app.post("/stream")
async def stream_llm_response(request: Request):
    # Get the prompt from the request body
    data = await request.json()
    user_prompt = data.get("prompt", "")
    
    return EventSourceResponse(
        event_generator(user_prompt),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
