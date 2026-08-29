"""
Event Schema
Defines the core event vocabulary and data structures for the Gateway and Pathway stream.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict


class EventLifecycle(str, Enum):
    REQUEST_RECEIVED = "request_received"
    EXECUTION_STARTED = "execution_started"
    LLM_EXECUTION = "llm_execution"
    TOOL_EXECUTION = "tool_execution"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Event:
    """Standardized event emitted during execution."""
    event_type: EventLifecycle
    request_id: str
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "payload": self.payload
        }
