"""
State Management
Defines minimal execution state tracked by the Gateway.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import time


@dataclass
class ExecutionState:
    """Tracks the state of a single execution request."""
    request_id: str
    status: str  # e.g., 'pending', 'running', 'completed', 'failed'
    start_time: float
    end_time: Optional[float] = None
    error: Optional[str] = None


class StateManager:
    """In-memory state manager to track execution lifecycle."""
    def __init__(self):
        self.states: Dict[str, ExecutionState] = {}

    def create_state(self, request_id: str) -> ExecutionState:
        state = ExecutionState(
            request_id=request_id,
            status="pending",
            start_time=time.time()
        )
        self.states[request_id] = state
        return state

    def update_state(self, request_id: str, status: str, error: Optional[str] = None) -> Optional[ExecutionState]:
        if request_id in self.states:
            state = self.states[request_id]
            state.status = status
            if error:
                state.error = error
            if status in ("completed", "failed"):
                state.end_time = time.time()
            return state
        return None

    def get_state(self, request_id: str) -> Optional[ExecutionState]:
        return self.states.get(request_id)
