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

from llama_mcp import BasicMCPClient, McpToolSpec
from util import load_system_prompt,load_json_prompt
from db.rag import RAG


def cprint(text: str, end: str = "", flush: bool = True):
    WORKFLOW_COLOR = '\033[36m'
    RESET = '\033[0m'
    print(f"{WORKFLOW_COLOR}{text}{RESET}", end=end, flush=flush)

base_dir=os.getenv("MCP_SRV_BASE_DIR")

class ProgressEvent(Event):
    msg: str

class ToolExecResultEvent(Event):
    result: str

class RAGEvent(Event):
    result: str

async def init_mcp_server():
    project_path = os.path.abspath(os.path.dirname(__file__))
    servers = [ 
        {"command_or_url":f"uv", "args":["--directory", project_path, "run", f"biz_app.py"]},
        #{"command_or_url":f"uv", "args":["--directory", project_path, "run", f"spb_server.py"]},
        {"command_or_url":"http://localhost:8081/sse", "args":[]},
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
            rag: RAG,
            memory: ChatMemoryBuffer = None,
            *args,
            **kwargs):
        # Initialize memory if not provided
        if memory is None:
            memory = ChatMemoryBuffer(token_limit=64000)
        self.memory = memory
        self.client = None
        self.llm = llm
        self.rag = rag
        #self.rag.create_index() # Create index for the first time
        #try:
            #self.rag.load_index()
        #except Exception as e:
            #self.rag.create_index() # Create index for the first time
            
        super().__init__(*args, **kwargs)
    
    def search_documents(self, query: str) -> str:
        """Useful for answering natural language questions about an personal essay written by Paul Graham."""
        logging.info(f"Searching documents with query: {query}")
        response = self.rag.query(query)
        logging.info(f"Search result: {response}")
        return str(response)

    @step
    async def process_input(self, ctx: Context, ev: StartEvent) -> Union[ToolExecResultEvent | StopEvent]:
        self.all_tools = await init_mcp_server()
        tools_name = [tool.metadata.name for tool in self.all_tools]
        # # Add event showing available tools
        ctx.write_event_to_stream(ProgressEvent(msg=f"Available tools: {tools_name}\n\n"))
        self.all_tools.append(self.search_documents)
        
        system_prompt=load_system_prompt(prompt_filename="system.txt", lang="zh")
        self.memory.put(ChatMessage(role=MessageRole.SYSTEM,content=system_prompt))

        query_info = AgentWorkflow.from_tools_or_functions(
            tools_or_functions=self.all_tools,
            llm=self.llm,
            system_prompt=system_prompt,
            verbose=False,
            timeout=180,
            )
        
        json_prompts = load_json_prompt("data_analysis.json", "zh")
        user_prompt = json_prompts["pre_analyze"].format(ev=ev)
        handler = query_info.run(user_msg=f'{user_prompt}. \n\n')

        response = ""
        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                print(event.delta, end="", flush=True)
                # ctx.write_event_to_stream(ProgressEvent(msg=event.delta))
                response += event.delta
            elif isinstance(event, ToolCallResult):
                ctx.write_event_to_stream(ProgressEvent(msg=f'{event.tool_name}: {event.tool_kwargs}\n\n'))
                ctx.write_event_to_stream(ProgressEvent(msg=f'{event.tool_output}\n'))

        self.memory.put(ChatMessage(role=MessageRole.ASSISTANT,content=response))
        return ToolExecResultEvent(result=response)
        
    @step
    async def process_rag(self, ctx: Context, ev: RAGEvent) -> ToolExecResultEvent:
        self.memory.put(ChatMessage(role=MessageRole.SYSTEM, content="You're an IIoT data analysis expert, and familar with SparkplugB specification. You task is to create different kinds of report that can help onsite engineers to understand the device status."))
        self.memory.put(ChatMessage(role=MessageRole.USER, content="Generate an IIoT report based on returned result input."))
        chat_history = self.memory.get()
        # print(chat_history)

        response = ""
        handle = await self.llm.astream_chat(chat_history)
        async for token in handle:
            cprint(token.delta)
            ctx.write_event_to_stream(ProgressEvent(msg=token.delta))
            response += token.delta
        return ToolExecResultEvent(result=response)

    @step
    async def gen_report(self, ctx: Context, ev: ToolExecResultEvent) -> StopEvent:
        user_prompt = load_json_prompt("data_analysis.json", "zh")["gen_report"]
        self.memory.put(ChatMessage(role=MessageRole.USER, content=user_prompt))
        chat_history = self.memory.get()

        response = ""
        handle = await self.llm.astream_chat(chat_history)
        async for token in handle:
            # cprint(token.delta)
            ctx.write_event_to_stream(ProgressEvent(msg=token.delta))
            response += token.delta
        return StopEvent(result=response)


async def main():
    try:
        llm = SiliconFlow(api_key=os.getenv("SFAPI_KEY"),model=os.getenv("MODEL_NAME"),temperature=0.2,max_tokens=4000, timeout=180)
        w = DemoFlow(timeout=None, llm=llm, verbose=True)
        ctx = Context(w)

        user_prompt = '''分析过去一周设备 test 的上线情况'''
        handler = w.run(user_input=user_prompt, ctx=ctx)

        async for ev in handler.stream_events():
            if isinstance(ev, ProgressEvent):
               cprint(ev.msg)
        await handler
    except Exception as e:
        cprint(f"An error occurred: {str(e)}\n")
        cprint("Full stack trace:\n")
        cprint(traceback.format_exc())
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())