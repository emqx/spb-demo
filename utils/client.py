import asyncio
import json
from contextlib import AsyncExitStack
from dataclasses import asdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function
from openai.types.shared_params.function_definition import FunctionDefinition

from .config import LLMClientConfig, LLMRequestConfig, MCPClientConfig

load_dotenv()

@dataclass
class MCPServer:
    srv_name: str
    session: ClientSession

    async def tool_existed(self, name: str) -> bool:
        response = await self.session.list_tools()
        return any(tool.name == name for tool in response.tools)

class MCPServers:
    servers: List[MCPServer] = []
    
    def add_mcp_server(self, name:str, session: ClientSession):
        server = MCPServer(srv_name=name, session=session)
        self.servers.append(server)

    async def get_tool_list(self) -> List[ChatCompletionToolParam]:
        all_tools = []
        for server in self.servers:
            tools = [
                ChatCompletionToolParam(
                    type="function",
                    function=FunctionDefinition(
                        name=tool.name,
                        description=tool.description if tool.description else "",
                        parameters=tool.inputSchema,
                    ),
                )
                for tool in (await server.session.list_tools()).tools
            ]
            all_tools.extend(tools)
        return all_tools

    async def find_tool(self, tool_name: str) -> List[MCPServer]:
        found_servers = []
        for server in self.servers:
            if await server.tool_existed(tool_name):
                found_servers.append(server)
        return found_servers

class MCPClient:
    def __init__(
        self,
        mpc_client_config: MCPClientConfig = MCPClientConfig(),
        llm_client_config: LLMClientConfig = LLMClientConfig(),
        llm_request_config: LLMRequestConfig = LLMRequestConfig("gpt-4o"),
    ):
        self.mpc_client_config = mpc_client_config
        self.llm_client_config = llm_client_config
        self.llm_request_config = llm_request_config
        self.llm_client = AsyncOpenAI(**asdict(self.llm_client_config))
        # self.server_sessions = MCPClient()
        self.mcp_servers = MCPServers()
        self.exit_stack = AsyncExitStack()
        print("CLIENT CREATED")

    async def connect_to_server(self, server_name: str):
        """Connect to an MCP server using its configuration name"""

        if server_name not in self.mpc_client_config.mcpServers:
            raise ValueError(
                f"Server '{server_name}' not found in MCP client configuration"
            )

        mcp_server_config = self.mpc_client_config.mcpServers[server_name]
        if not mcp_server_config.enabled:
            raise ValueError(f"Server '{server_name}' is disabled")

        stdio_server_params = StdioServerParameters(**asdict(mcp_server_config))

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(stdio_server_params)
        )
        self.stdio, self.write = stdio_transport
        session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        await session.initialize()  # type: ignore
        # List available tools
        response = await session.list_tools()  # type: ignore
        print(f"CLIENT CONNECT to {server_name}")
        print("AVAILABLE TOOLS", [tool.name for tool in response.tools])
        self.mcp_servers.add_mcp_server(server_name, session)

    async def process_tool_call(self, tool_call) -> ChatCompletionToolMessageParam:
        match tool_call.type:
            case "function":
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                print(f"##############################{tool_call}: {tool_args}")
                
                servers = await self.mcp_servers.find_tool(tool_name)
                if len(servers) > 1:
                    print(f"Multiple servers found with tool {tool_name}, using the first one")
                elif len(servers) == 0:
                    raise ValueError(f"Cannot find any server with tool {tool_name}")
                selected_server = servers[0]
                call_tool_result = await selected_server.session.call_tool(tool_name, tool_args)

                if call_tool_result.isError:
                    raise ValueError("An error occurred while calling the tool.")

                results = []
                for result in call_tool_result.content:
                    match result.type:
                        case "text":
                            results.append(result.text)
                        case "image":
                            raise NotImplementedError("Image content is not supported")
                        case "resource":
                            raise NotImplementedError(
                                "Embedded resource is not supported"
                            )
                        case _:
                            raise ValueError(f"Unknown content type: {result.type}")

                return ChatCompletionToolMessageParam(
                    role="tool",
                    content=json.dumps({**tool_args, tool_name: results}),
                    tool_call_id=tool_call.id,
                )

            case _:
                raise ValueError(f"Unknown tool call type: {tool_call.type}")

    async def process_messages(
        self,
        messages: list[ChatCompletionMessageParam],
        llm_request_config: LLMRequestConfig | None = None,
    ) -> list[ChatCompletionMessageParam]:
        # Set up tools and LLM request config
        if not self.mcp_servers.servers or len(self.mcp_servers.servers) == 0:
            raise RuntimeError("No servers connected")
        tools = await self.mcp_servers.get_tool_list()
        llm_request_config = LLMRequestConfig(
            **{
                **asdict(self.llm_request_config),
                **(asdict(llm_request_config) if llm_request_config else {}),
            }
        )

        last_message_role = messages[-1]["role"]
        print(f"###########################: {last_message_role}")

        match last_message_role:
            case "user":
                response = await self.llm_client.chat.completions.create(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    **asdict(llm_request_config),
                )

                finish_reason = response.choices[0].finish_reason
                match finish_reason:
                    case "stop":
                        messages.append(
                            ChatCompletionAssistantMessageParam(
                                role="assistant",
                                content=response,
                            )
                        )
                        return messages

                    case "tool_calls":
                        tool_calls = response.choices[0].message.tool_calls
                        print(response.choices[0].message)
                        assert tool_calls is not None
                        messages.append(
                            ChatCompletionAssistantMessageParam(
                                role="assistant",
                                tool_calls=[
                                    ChatCompletionMessageToolCallParam(
                                        id=tool_call.id,
                                        function=Function(
                                            arguments=tool_call.function.arguments,
                                            name=tool_call.function.name,
                                        ),
                                        type=tool_call.type,
                                    )
                                    for tool_call in tool_calls
                                ],
                            )
                        )
                        tasks = [
                            asyncio.create_task(self.process_tool_call(tool_call))
                            for tool_call in tool_calls
                        ]
                        messages.extend(await asyncio.gather(*tasks))
                        return await self.process_messages(messages, llm_request_config)
                    case "length":
                        raise ValueError("Length limit reached")
                    case "content_filter":
                        raise ValueError("Content filter triggered")
                    case "function_call":
                        raise NotImplementedError("Function call not implemented")
                    case _:
                        raise ValueError(f"Unknown finish reason: {finish_reason}")

            case "assistant":
                # NOTE: the only purpose of this case is to trigger other tool
                # calls based on the results of the previous tool calls
                response = await self.llm_client.chat.completions.create(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    **asdict(llm_request_config),
                )
                print(response.choices[0].finish_reason)
                finish_reason = response.choices[0].finish_reason

                match finish_reason:
                    case "stop":
                        # NOTE: we do not add the last response message
                        return messages

                    case "tool_calls":
                        tool_calls = response.choices[0].message.tool_calls
                        assert tool_calls is not None
                        messages.append(
                            ChatCompletionAssistantMessageParam(
                                role="assistant",
                                tool_calls=[
                                    ChatCompletionMessageToolCallParam(
                                        id=tool_call.id,
                                        function=Function(
                                            arguments=tool_call.function.arguments,
                                            name=tool_call.function.name,
                                        ),
                                        type=tool_call.type,
                                    )
                                    for tool_call in tool_calls
                                ],
                            )
                        )
                        results_messages = [
                            await self.process_tool_call(tool_call)
                            for tool_call in tool_calls
                        ]
                        messages.extend(results_messages)
                        return await self.process_messages(messages, llm_request_config)
                    case "length":
                        raise ValueError("Length limit reached")
                    case "content_filter":
                        raise ValueError("Content filter triggered")
                    case "function_call":
                        raise NotImplementedError("Function call not implemented")
                    case _:
                        raise ValueError(f"Unknown finish reason: {finish_reason}")

            case "tool":
                response = await self.llm_client.chat.completions.create(
                    messages=messages,
                    stream= True,
                    **asdict(llm_request_config),
                )
                response_text = ""
                finish_reason = ""
                async for event in response:
                    response_text += event.choices[0].delta.content
                    finish_reason = event.choices[0].finish_reason
                    print(event.choices[0].delta.content, end="", flush=True)

                match finish_reason:
                    case "stop":
                        messages.append(
                            ChatCompletionAssistantMessageParam(
                                role="assistant",
                                content=response_text,
                            )
                        )

                        return await self.process_messages(messages, llm_request_config)
                    case "tool_calls":
                        raise ValueError(
                            "The message following a tool message cannot be a tool call"
                        )
                    case "length":
                        raise ValueError("Length limit reached")
                    case "content_filter":
                        raise ValueError("Content filter triggered")
                    case "function_call":
                        raise NotImplementedError("Function call not implemented")
                    case _:
                        raise ValueError(f"Unknown finish reason: {finish_reason}")

            case "developer":
                raise NotImplementedError("Developer messaages are not supported")
            case "system":
                raise NotImplementedError("System messages are not supported")
            case "function":
                raise NotImplementedError("System messages are not supported")
            case _:
                raise ValueError(f"Invalid message role: {last_message_role}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
