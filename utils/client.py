import asyncio
import json
from contextlib import AsyncExitStack
from dataclasses import asdict
from typing import Optional

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
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.current_server = None

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
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()  # type: ignore
        self.current_server = server_name

        # List available tools
        response = await self.session.list_tools()  # type: ignore
        print(f"CLIENT CONNECT to {server_name}")
        print("AVAILABLE TOOLS", [tool.name for tool in response.tools])

    async def process_tool_call(self, tool_call) -> ChatCompletionToolMessageParam:
        match tool_call.type:
            case "function":
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                print(f"##############################{tool_call}: {tool_args}")
                call_tool_result = await self.session.call_tool(tool_name, tool_args)  # type: ignore

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
        if not self.session:
            raise RuntimeError("Not connected to any server")
        tools = [
            ChatCompletionToolParam(
                type="function",
                function=FunctionDefinition(
                    name=tool.name,
                    description=tool.description if tool.description else "",
                    parameters=tool.inputSchema,
                ),
            )
            for tool in (await self.session.list_tools()).tools
        ]
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
