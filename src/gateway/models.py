"""
Gateway Models
Defines the strict contracts between the API layer and the Gateway Core.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GatewayRequest:
    """The normalized request expected by the Gateway from the API layer."""
    request_id: str
    messages: List[Dict[str, Any]]
    session_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayResponse:
    """The normalized response returned by the Gateway to the API layer."""
    request_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "request_id": self.request_id,
            "status": self.status,
            "execution_time_ms": self.execution_time_ms
        }
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        return data
