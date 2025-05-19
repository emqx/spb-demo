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

def get_rag() -> RAG:
    rag = RAG()
    try:
        rag.load_index_from_hybrid_chunks()
    except Exception as e:
        rag.create_index_from_hybrid_chunks("./data/3HAC066553-010_20250426183500.md")
    return rag

rag = get_rag()

def search_error_info_by_code(query: str) -> str:
    """
    Search for error information in the document vector database using a query string.

    This function uses a RAG (Retrieval-Augmented Generation) system to search through
    indexed documents and retrieve relevant error information based on the provided query.

    Args:
        query (str): The search query string, typically an error code or error-related text.
        E,g: 10040, 10091 etc.

    Returns:
        str: The search response containing relevant error information found in the documents.

    Logs:
        - Logs the input query at INFO level
        - Logs the search result at INFO level

    Example:
        >>> result = search_error_info_by_code("10042")
        >>> print(result)
        "10042 Axis synchronized Description
        A fine calibration or update of revolution counter(s) was made...."
    """
    logging.info(f"Searching documents with query: {query}")
    response = rag.query(query)
    logging.info(f"Search result: {response}")
    return str(response)

class DemoFlow(Workflow):
    def __init__(
            self,
            llm: OpenAILike,
            memory: ChatMemoryBuffer = None,
            *args,
            **kwargs):
        # Initialize memory if not provided
        if memory is None:
            memory = ChatMemoryBuffer(token_limit=64000)
        self.memory = memory
        self.client = None
        self.llm = llm
        super().__init__(*args, **kwargs)
    
    

    @step
    async def process_input(self, ctx: Context, ev: StartEvent) -> Union[ RAGEvent | StopEvent]:
        self.all_tools = await init_mcp_server()
        tools_name = [tool.metadata.name for tool in self.all_tools]
        # # Add event showing available tools
        ctx.write_event_to_stream(ProgressEvent(msg=f"Available tools: {tools_name}\n\n"))
        
        system_prompt=load_system_prompt(prompt_filename="system.txt", lang="zh").format(ev=ev)
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
        self.memory.put(ChatMessage(role=MessageRole.USER,content=user_prompt))

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
        return RAGEvent(result=response)
        
    @step
    async def process_rag(self, ctx: Context, ev: RAGEvent) -> ToolExecResultEvent:
        json_prompts = load_json_prompt("data_analysis.json", "zh")
        user_prompt = json_prompts["extract_diagnose"].format(ev=ev)
        print(user_prompt)
        self.memory.put(ChatMessage(role=MessageRole.USER,content=user_prompt))

        flow = AgentWorkflow.from_tools_or_functions([search_error_info_by_code], llm=self.llm, system_prompt="")
        response = ""
        handler = flow.run(user_msg=user_prompt)
        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                response += event.delta
                cprint(event.delta)
            elif isinstance(event, ToolCallResult):
                print(f'{event.tool_name}: {event.tool_kwargs}\n\n')

        self.memory.put(ChatMessage(role=MessageRole.ASSISTANT,content=response))
        return ToolExecResultEvent(result="")

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