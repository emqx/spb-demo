from llama_index.tools.mcp import McpToolSpec
from llama_index.core.agent.workflow import FunctionAgent, ToolCallResult, ToolCall
from llama_index.core.workflow import Context
from llama_index.llms.siliconflow import SiliconFlow
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
import os
from dotenv import load_dotenv 
import traceback

SYSTEM_PROMPT = """\
You are an AI assistant for IT asset manager.

You task is to leverage the tools to get the correct information for user.
"""
load_dotenv()

llm = SiliconFlow(api_key=os.getenv("SF_API_KEY"),model=os.getenv("MODEL_NAME"),temperature=0.6,max_tokens=4000, timeout=180)

async def get_agent(tools: McpToolSpec):
    tools = await tools.to_tool_list_async()
    agent = FunctionAgent(
        name="Agent",
        description="An agent that can get the detailed result for the factory.",
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent


async def handle_user_message(
    message_content: str,
    agent: FunctionAgent,
    agent_context: Context,
    verbose: bool = False,
):
    handler = agent.run(message_content, ctx=agent_context)
    async for event in handler.stream_events():
        if verbose and type(event) == ToolCall:
            print(f"Calling tool {event.tool_name} with kwargs {event.tool_kwargs}")
        elif verbose and type(event) == ToolCallResult:
            print(f"Tool {event.tool_name} returned {event.tool_output}")

    response = await handler
    return str(response)

async def main():
    try:
        print("Here....")
        # We consider there is a mcp server running on 127.0.0.1:8000, or you can use the mcp client to connect to your own mcp server.
        mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
        mcp_tool = McpToolSpec(client=mcp_client)

        # get the agent
        agent = await get_agent(mcp_tool)
        # create the agent context
        agent_context = Context(agent)
        # Run the agent!
        while True:
            user_input = input("Enter your message: ")
            if user_input == "exit":
                break
            print("User: ", user_input)
            response = await handle_user_message(user_input, agent, agent_context, verbose=True)
            print("Agent: ", response)
    except Exception as e:
        print(f"Error processing message: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())        