from dataclasses import dataclass, field
from typing import Literal

from openai import NOT_GIVEN, NotGiven
from openai.types.chat import ChatCompletionReasoningEffort


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""

    command: str
    args: list[str]
    env: dict[str, str] | None = None
    description: str | None = None
    enabled: bool = True


@dataclass
class MCPClientConfig:
    """Configuration for the MCP client"""

    mcpServers: dict[str, MCPServerConfig] = field(default_factory=dict)


@dataclass
class LLMClientConfig:
    """Configuration for the OpenAI (compatible) client."""

    api_key: str | None = None
    organization: str | None = None
    project: str | None = None
    base_url: str | None = None


@dataclass
class LLMRequestConfig:
    """Configuration for OpenAI client.chat.completions.create.

    Notes:
        - messages are not part of LLM request config
        - tools/tool_choice are handle directly by the MCP client
    """

    model: str
    temperature: float | NotGiven | None = NOT_GIVEN
    # top_p: float | NotGiven | None = NOT_GIVEN
    # max_tokens: int | NotGiven | None = NOT_GIVEN
    # reasoning_effort: ChatCompletionReasoningEffort | NotGiven = NOT_GIVEN
    # stream: NotGiven | Literal[False] | None = NOT_GIVEN
    # stop: str | list[str] | NotGiven | None = NOT_GIVEN
    # seed: int | NotGiven | None = NOT_GIVEN
    # presence_penalty: float | NotGiven | None = NOT_GIVEN
    # frequency_penalty: float | NotGiven | None = NOT_GIVEN
    # logit_bias: dict[str, int] | NotGiven | None = NOT_GIVEN
