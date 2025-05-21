import os
from typing import Any, Union
import logging
import traceback

from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
    Context,
)

from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage, MessageRole 
from llama_index.core.agent.workflow import (AgentWorkflow, AgentStream, ToolCallResult)
from llama_index.llms.openai_like import OpenAILike
from llama_index.llms.siliconflow import SiliconFlow

from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from util import load_system_prompt,load_json_prompt

def cprint(text: str, end: str = "", flush: bool = True):
    WORKFLOW_COLOR = '\033[36m'
    RESET = '\033[0m'
    print(f"{WORKFLOW_COLOR}{text}{RESET}", end=end, flush=flush)

base_dir=os.getenv("MCP_SRV_BASE_DIR")


class ProgressEvent(Event):
    msg: str

class ToolExecResultEvent(Event):
    result: str

async def init_mcp_server():
    project_path = os.path.abspath(os.path.dirname(__file__))
    servers = [ 
        #{"command_or_url":f"uv", "args":["--directory", project_path, "run", f"biz_app.py"]},
        #{"command_or_url":f"uv", "args":["--directory", project_path, "run", f"spb_server.py"]},
        {"command_or_url":"http://localhost:8081/sse", "args":[]},
        {"command_or_url":"http://localhost:8082/sse", "args":[]},
    ]
    all_tools = []
    for server in servers:
        mcp_client = BasicMCPClient(
            command_or_url=server["command_or_url"],
            args=server["args"]
        )
        mcp_tool = McpToolSpec(client=mcp_client)
        #tools = mcp_tool.to_tool_list()
        tools = await mcp_tool.to_tool_list_async()
        all_tools.extend(tools)   
    return all_tools

class DemoFlow(Workflow):
    def __init__(
            self,
            llm: OpenAILike,
            lang: str = "zh",
            memory: ChatMemoryBuffer = None,
            *args,
            **kwargs):
        # Initialize memory if not provided
        if memory is None:
            memory = ChatMemoryBuffer(token_limit=64000)
        self.memory = memory
        self.lang = lang
        self.client = None
        self.llm = llm
        super().__init__(*args, **kwargs)

    @step
    async def query_data(self, ctx: Context, ev: StartEvent) -> Union[ ToolExecResultEvent | StopEvent]:
        self.all_tools = await init_mcp_server()
        tools_name = [tool.metadata.name for tool in self.all_tools]
        # # Add event showing available tools
        ctx.write_event_to_stream(ProgressEvent(msg=f"Available tools: {tools_name}\n\n"))

        system_prompt=load_system_prompt(prompt_filename="system.txt", lang=self.lang).format(ev=ev)
        self.memory.put(ChatMessage(role=MessageRole.SYSTEM,content=system_prompt))

        query_info = AgentWorkflow.from_tools_or_functions(
            tools_or_functions=self.all_tools,
            llm=self.llm,
            system_prompt=system_prompt,
            verbose=False,
            timeout=180,
            )
        
        json_prompts = load_json_prompt("data_analysis.json", self.lang)
        user_prompt = json_prompts["pre_analyze"].format(ev=ev)
        await ctx.set("user_input", ev.user_input)
        self.memory.put(ChatMessage(role=MessageRole.USER,content=user_prompt))

        handler = query_info.run(user_msg=f'{user_prompt}. \n\n')

        response = ""
        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                cprint(event.delta, end="", flush=True)
                response += event.delta
                # ctx.write_event_to_stream(ProgressEvent(msg=event.delta))
            elif isinstance(event, ToolCallResult):
                ctx.write_event_to_stream(ProgressEvent(msg=f'{event.tool_name}: {event.tool_kwargs}\n\n'))
                ctx.write_event_to_stream(ProgressEvent(msg=f'{event.tool_output}\n'))

        self.memory.put(ChatMessage(role=MessageRole.ASSISTANT,content=response))
        return ToolExecResultEvent(result=response)

    @step
    async def gen_report(self, ctx: Context, ev: ToolExecResultEvent) -> StopEvent:
        ev.user_input = await ctx.get("user_input")
        user_prompt = load_json_prompt("data_analysis.json", self.lang)["gen_report"].format(ev=ev)
        self.memory.put(ChatMessage(role=MessageRole.USER, content=user_prompt))
        chat_history = self.memory.get()

        response = ""
        handle = await self.llm.astream_chat(chat_history)
        async for token in handle:
            # cprint(token.delta)
            ctx.write_event_to_stream(ProgressEvent(msg=token.delta))
            response += token.delta
        return StopEvent(result=response)