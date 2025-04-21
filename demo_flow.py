import os
from typing import Any, Union

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


def cprint(text: str, end: str = "", flush: bool = True):
    WORKFLOW_COLOR = '\033[36m'
    RESET = '\033[0m'
    print(f"{WORKFLOW_COLOR}{text}{RESET}", end=end, flush=flush)

base_dir=os.getenv("MCP_SRV_BASE_DIR")

class ProgressEvent(Event):
    msg: str

class ToolExecResultEvent(Event):
    result: str

class DemoFlow(Workflow):
    def __init__(
            self,
            llm: OpenAILike,
            memory: ChatMemoryBuffer = None,
            *args,
            **kwargs):
        self.memory = memory or ChatMemoryBuffer(token_limit=8000)
        self.client = None
        self.llm = llm
        super().__init__(*args, **kwargs)
        

    @step
    async def process_input(self, ctx: Context, ev: StartEvent) -> Union[ToolExecResultEvent | StopEvent]:
        project_path = os.path.abspath(os.path.dirname(__file__))
        ctx.write_event_to_stream(ProgressEvent(msg=f"Connectting to MCP servers.\n\n"))
        servers = [ 
            {"command_or_url":f"uv", "args":["--directory", project_path, "run", f"biz_app.py"]},
            {"command_or_url":f"uv", "args":["--directory", project_path, "run", f"spb_server.py"]},
        ]

        all_tools = []
        for server in servers:
            mcp_client = BasicMCPClient(
                command_or_url=server["command_or_url"],
                args=server["args"]
            )
            mcp_tool = McpToolSpec(client=mcp_client)
            tools = await mcp_tool.to_tool_list_async()
            all_tools.extend(tools)

        # Add event showing available tools
        tool_names = ", ".join([tool.metadata.name for tool in all_tools])
        ctx.write_event_to_stream(ProgressEvent(msg=f"Available tools: {tool_names}\n\n"))

        system_prompt="You have a set of tools to extract the useful information from external database system, which stores related Sparkplug data. You task is to use the tools extract the right information for user's input."
        self.memory.put(ChatMessage(role=MessageRole.SYSTEM,content=system_prompt))

        query_info = AgentWorkflow.from_tools_or_functions(
            tools_or_functions=all_tools,
            llm=self.llm,
            system_prompt=system_prompt,
            verbose=False
            )
        
        handler = query_info.run(user_msg=f'{ev.user_input}. Notice: NEVER surround your response with markdown code markers.')
        response = ""
        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                print(event.delta, end="", flush=True)
                # ctx.write_event_to_stream(ProgressEvent(msg=event.delta))
                response += event.delta
            elif isinstance(event, ToolCallResult):
                ctx.write_event_to_stream(ProgressEvent(msg=f'{event.tool_name}: {event.tool_kwargs}\n\n'))
                # ctx.write_event_to_stream(ProgressEvent(msg=f'{event.tool_output}\n'))
            # elif isinstance(event, ToolCallResult):
            #     print(event.tool_output, end="\n", flush=True)

        
        self.memory.put(ChatMessage(role=MessageRole.ASSISTANT, content=response))
        return ToolExecResultEvent(result=response)
        
    @step
    async def gen_report(self, ctx: Context, ev: ToolExecResultEvent) -> StopEvent:
        self.memory.put(ChatMessage(role=MessageRole.SYSTEM, content="You're an IIoT data analysis expert, and familar with SparkplugB specification. You task is to create different kinds of report that can help onsite engineers to understand the device status."))
        self.memory.put(ChatMessage(role=MessageRole.USER, content="Generate a IIoT report based on user's input."))
        chat_history = self.memory.get()

        response = ""
        handle = await self.llm.astream_chat(chat_history)
        async for token in handle:
            # cprint(token.delta)
            ctx.write_event_to_stream(ProgressEvent(msg=token.delta))
            response += token.delta
        return StopEvent(result=response)


async def main():
    llm = SiliconFlow(api_key=os.getenv("SFAPI_KEY"),model=os.getenv("MODEL_NAME"),temperature=0.2,max_tokens=4000, timeout=180)
    w = DemoFlow(timeout=None, llm=llm, verbose=True)
    ctx = Context(w)

    user_prompt = '''Query the offline status of  "Big boy" of last week.'''
    handler = w.run(user_input=user_prompt, ctx=ctx)

    async for ev in handler.stream_events():
        if isinstance(ev, ProgressEvent):
           cprint(ev.msg)
    await handler


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())