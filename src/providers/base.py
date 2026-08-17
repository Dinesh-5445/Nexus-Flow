"""
Provider Abstraction Layer - Base Interfaces and Data Structures.
Defines standardized data structures for LLM messages, responses, tool calls,
and the abstract base class for all LLM providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import os
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """Represents a standardized tool call request emitted by an LLM."""
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMMessage:
    """Represents a single message in an LLM conversation."""
    role: str  # e.g., 'system', 'user', 'assistant', 'tool'
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "role": self.role,
            "content": self.content
        }
        if self.name:
            data["name"] = self.name
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        return data


@dataclass
class LLMResponse:
    """Normalized response returned by any concrete LLM provider."""
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    model: str = ""
    finish_reason: str = "stop"  # e.g., 'stop', 'tool_calls', 'length'
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        """Returns True if the model requested one or more tool calls."""
        return len(self.tool_calls) > 0


@dataclass
class ProviderConfig:
    """Configuration settings for an LLM provider."""
    api_key: Optional[str] = None
    model_name: str = "default-model"
    temperature: float = 0.7
    max_tokens: int = 1024
    timeout_seconds: float = 30.0
    extra_params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, prefix: str = "PROVIDER_") -> "ProviderConfig":
        """
        Creates a ProviderConfig by reading environment variables with a specified prefix,
        ensuring secrets are not hardcoded in the codebase.
        """
        return cls(
            api_key=os.getenv(f"{prefix}API_KEY"),
            model_name=os.getenv(f"{prefix}MODEL_NAME", "default-model"),
            temperature=float(os.getenv(f"{prefix}TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv(f"{prefix}MAX_TOKENS", "1024")),
            timeout_seconds=float(os.getenv(f"{prefix}TIMEOUT_SECONDS", "30.0")),
        )


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for LLM providers.
    All concrete providers (e.g. OpenAI, Anthropic, Gemini, Mock) implement this interface.
    """

    def __init__(self, config: Optional[ProviderConfig] = None):
        self.config = config or ProviderConfig()

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Asynchronously generates a normalized response from the LLM given conversation messages
        and optional tool schemas.
        """
        pass
