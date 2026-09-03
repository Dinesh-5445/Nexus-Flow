"""
Gateway Router
Responsible for receiving requests from the API service layer and triggering the orchestrator.
"""

import time
from .models import GatewayRequest, GatewayResponse
from ..orchestration.executor import Orchestrator
from ..state.manager import StateManager
from ..events.schema import Event, EventLifecycle
from ..events.stream import EventStream


class GatewayRouter:
    def __init__(self, orchestrator: Orchestrator, state_manager: StateManager, event_stream: EventStream):
        self.orchestrator = orchestrator
        self.state_manager = state_manager
        self.event_stream = event_stream

    async def handle_request(self, request: GatewayRequest) -> GatewayResponse:
        """
        Receives validated API requests and initiates the orchestration flow.
        """
        start_time = time.perf_counter()
        
        if not request or not getattr(request, "request_id", None):
            return GatewayResponse(
                request_id="unknown",
                status="failed",
                error="Invalid request: missing request_id",
                execution_time_ms=0.0
            )
            
        try:
            # 1. Initialize State
            state = self.state_manager.create_state(request.request_id)
            
            # 2. Publish REQUEST_RECEIVED event
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.REQUEST_RECEIVED,
                    request_id=request.request_id,
                    payload={"session_id": getattr(request, "session_id", ""), "messages_count": len(getattr(request, "messages", []))}
                )
            )
            
            # 3. Call Orchestrator
            self.state_manager.update_state(request.request_id, "running")
            result = await self.orchestrator.execute_flow(request)
            
            # 4. Success Completion
            self.state_manager.update_state(request.request_id, "completed")
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.COMPLETED,
                    request_id=request.request_id,
                    payload={"status": "success"}
                )
            )
            
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return GatewayResponse(
                request_id=request.request_id,
                status="success",
                result=result,
                execution_time_ms=round(duration_ms, 2)
            )
            
        except Exception as e:
            # 5. Failure Path
            # Update state safely
            try:
                self.state_manager.update_state(request.request_id, "failed", error=str(e))
            except Exception:
                pass
                
            try:
                await self.event_stream.publish(
                    Event(
                        event_type=EventLifecycle.FAILED,
                        request_id=request.request_id,
                        payload={"error": str(e)}
                    )
                )
            except Exception:
                pass
            
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return GatewayResponse(
                request_id=request.request_id,
                status="failed",
                error=str(e),
                execution_time_ms=round(duration_ms, 2)
            )
