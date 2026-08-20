"""
Tool Abstraction Layer - Base Interfaces and Result Structures.
Defines the abstract BaseTool and normalized ToolResult data structures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import time
from typing import Any, Dict, Optional
from ..events.schema import EventLifecycle


@dataclass
class ToolResult:
    """
    Normalized result of executing a tool call.
    Includes execution timing, error handling, and event payload formatting.
    """
    tool_call_id: str
    tool_name: str
    status: str  # 'completed' or 'failed'
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.status == "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }

    def to_event_payload(self, request_id: str, session_id: str = "") -> Dict[str, Any]:
        """
        Formats the tool execution as an event payload adhering to the shared
        event contract expected by Dinesh's event stream and Koushik's Watchdog.
        """
        return {
            "request_id": request_id,
            "event_type": EventLifecycle.TOOL_EXECUTION.value,
            "timestamp": time.time(),
            "tool_name": self.tool_name,
            "status": self.status,
            "session_id": session_id,
            "tool_call_id": self.tool_call_id,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
        }


class BaseTool(ABC):
    """
    Abstract Base Class for all tools executable within NexusFlow.
    """

    name: str = ""
    description: str = ""
    parameters_schema: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """
        Asynchronously executes the tool logic with keyword arguments.
        """
        pass

    def to_schema(self) -> Dict[str, Any]:
        """
        Returns standard JSON schema for function/tool calling with LLMs.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
