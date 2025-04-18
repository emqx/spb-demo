from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from llama_index.llms.siliconflow import SiliconFlow
from spb_flow import DemoFlow, Context, ProgressEvent
import os
from dotenv import load_dotenv
import asyncio
from sse_starlette.sse import EventSourceResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json

load_dotenv()

app = FastAPI()

# Add after creating the FastAPI app
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("index.html")

async def event_generator(prompt: str):
    # Initialize the LLM and workflow
    llm = SiliconFlow(
        api_key=os.getenv("SF_API_KEY"),
        model=os.getenv("MODEL_NAME"),
        temperature=0.6,
        max_tokens=4000,
        timeout=180
    )
    workflow = DemoFlow(timeout=None, llm=llm, verbose=True)
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
                    "data": f'{json.dumps({'content': ev.msg})}\n\n'
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
