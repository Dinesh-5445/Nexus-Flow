import unittest
import asyncio
from src.gateway.models import GatewayRequest
from src.gateway.router import GatewayRouter
from src.orchestration.executor import Orchestrator
from src.state.manager import StateManager
from src.events.stream import EventStream
from src.events.schema import EventLifecycle
from src.providers.mock_provider import MockProvider
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry
from src.tools.builtin import CalculatorTool

from src.providers.base import LLMResponse, ToolCall
import uuid

class TestGatewayOrchestrationFlow(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 1. Setup Tool Executor and Mock Provider
        self.registry = ToolRegistry()
        self.registry.register(CalculatorTool())
        self.tool_executor = ToolExecutor(registry=self.registry)
        
        # Pre-program mock provider to request a tool call
        self.mock_provider = MockProvider()
        self.mock_provider.predefined_responses.append(
            LLMResponse(
                content="I will calculate that.",
                tool_calls=[
                    ToolCall(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name="calculator",
                        arguments={"expression": "5 + 3"}
                    )
                ]
            )
        )
        
        # 2. Setup Events, State, Orchestrator
        self.event_stream = EventStream()
        self.state_manager = StateManager()
        self.orchestrator = Orchestrator(
            provider=self.mock_provider,
            tool_executor=self.tool_executor,
            event_stream=self.event_stream
        )
        
        # 3. Setup Gateway
        self.gateway = GatewayRouter(
            orchestrator=self.orchestrator,
            state_manager=self.state_manager,
            event_stream=self.event_stream
        )

    async def test_successful_execution_flow(self):
        request = GatewayRequest(
            request_id="req-123",
            session_id="session-456",
            messages=[{"role": "user", "content": "Calculate 5 + 3"}]
        )
        
        response = await self.gateway.handle_request(request)
        
        # Verify Gateway Response
        if response.status != "success":
            print(f"FAILED WITH ERROR: {response.error}")
        self.assertEqual(response.status, "success")
        self.assertEqual(response.request_id, "req-123")
        self.assertIsNotNone(response.result)
        self.assertIn("tool_results", response.result)
        self.assertEqual(len(response.result["tool_results"]), 1)
        self.assertEqual(response.result["tool_results"][0]["result"]["result"], 8)
        
        # Verify State
        state = self.state_manager.get_state("req-123")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "completed")
        
        # Verify Events
        events = self.event_stream.published_events
        self.assertEqual(len(events), 5)
        
        event_types = [e.event_type for e in events]
        self.assertEqual(event_types, [
            EventLifecycle.REQUEST_RECEIVED,
            EventLifecycle.EXECUTION_STARTED,
            EventLifecycle.LLM_EXECUTION,
            EventLifecycle.TOOL_EXECUTION,
            EventLifecycle.COMPLETED
        ])
        
        # Check specific event payload
        tool_event = events[3]
        self.assertEqual(tool_event.event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(tool_event.payload["tool_name"], "calculator")
        self.assertEqual(tool_event.payload["status"], "completed")

    async def test_failed_execution_flow(self):
        # We can simulate a failure by breaking the orchestrator artificially, 
        # or passing invalid tool info if the provider triggers it.
        # But a simple way is to pass a request that causes a known failure in mock provider or tool.
        # Actually, if we just pass a request without mock response, MockProvider will return a generic response
        # which will succeed. Let's create an error by passing a bad message structure to trigger exception.
        
        request = GatewayRequest(
            request_id="req-bad",
            messages=[{"bad_key": "user", "wrong_content": "fail"}] # Missing role/content
        )
        
        response = await self.gateway.handle_request(request)
        
        # Verify Gateway Response caught the error
        self.assertEqual(response.status, "failed")
        self.assertIsNotNone(response.error)
        
        # Verify State
        state = self.state_manager.get_state("req-bad")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "failed")
        
        # Verify Events (REQUEST_RECEIVED -> EXECUTION_STARTED -> FAILED)
        events = self.event_stream.published_events
        # Filter for this specific request
        events = [e for e in events if e.request_id == "req-bad"]
        self.assertEqual(len(events), 3)
        
        event_types = [e.event_type for e in events]
        self.assertEqual(event_types, [
            EventLifecycle.REQUEST_RECEIVED,
            EventLifecycle.EXECUTION_STARTED,
            EventLifecycle.FAILED
        ])

    async def test_provider_failure(self):
        class FailingProvider(MockProvider):
            async def generate(self, *args, **kwargs):
                raise ValueError("Provider API is down")
        
        # Use a fresh event stream and state manager for this instance, or just swap the provider temporarily
        original_provider = self.gateway.orchestrator.provider
        self.gateway.orchestrator.provider = FailingProvider()
        
        request = GatewayRequest(
            request_id="req-prov-fail",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = await self.gateway.handle_request(request)
        
        # Restore original provider
        self.gateway.orchestrator.provider = original_provider
        
        # Verify Gateway Response caught the error
        self.assertEqual(response.status, "failed")
        self.assertIn("Provider API is down", response.error)
        
        # Verify State
        state = self.state_manager.get_state("req-prov-fail")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "failed")
        
        events = [e for e in self.event_stream.published_events if e.request_id == "req-prov-fail"]
        self.assertEqual(len(events), 3)
        event_types = [e.event_type for e in events]
        self.assertEqual(event_types, [
            EventLifecycle.REQUEST_RECEIVED,
            EventLifecycle.EXECUTION_STARTED,
            EventLifecycle.FAILED
        ])

    async def test_tool_failure(self):
        self.mock_provider.predefined_responses.clear()
        self.mock_provider.predefined_responses.append(
            LLMResponse(
                content="I will calculate that.",
                tool_calls=[
                    ToolCall(
                        id="call_bad",
                        name="calculator",
                        arguments={"expression": "invalid math"}
                    )
                ]
            )
        )
        
        request = GatewayRequest(
            request_id="req-tool-fail",
            messages=[{"role": "user", "content": "Calculate something bad"}]
        )
        
        response = await self.gateway.handle_request(request)
        
        # Overall request should succeed, but tool result will have failed
        self.assertEqual(response.status, "success")
        self.assertIsNotNone(response.result)
        tool_res = response.result["tool_results"][0]
        self.assertEqual(tool_res["status"], "failed")
        self.assertIn("error", tool_res)
        
        events = [e for e in self.event_stream.published_events if e.request_id == "req-tool-fail"]
        event_types = [e.event_type for e in events]
        self.assertIn(EventLifecycle.TOOL_EXECUTION, event_types)
        
        tool_event = next(e for e in events if e.event_type == EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(tool_event.payload["status"], "failed")

    async def test_invalid_request_missing_id(self):
        request = GatewayRequest(
            request_id="",
            messages=[{"role": "user", "content": "Hello"}]
        )
        response = await self.gateway.handle_request(request)
        self.assertEqual(response.status, "failed")
        self.assertIn("missing request_id", response.error.lower())
        self.assertEqual(response.request_id, "unknown")

    async def test_execution_isolation(self):
        self.mock_provider.predefined_responses.clear()
        self.mock_provider.predefined_responses.extend([
            LLMResponse(content="Success 1", tool_calls=[]),
            LLMResponse(content="Success 2", tool_calls=[])
        ])

        request1 = GatewayRequest(request_id="req-iso-1", messages=[{"role": "user", "content": "Req 1"}])
        request2 = GatewayRequest(request_id="req-iso-2", messages=[{"role": "user", "content": "Req 2"}])

        # Execute concurrently
        response1, response2 = await asyncio.gather(
            self.gateway.handle_request(request1),
            self.gateway.handle_request(request2)
        )

        self.assertEqual(response1.status, "success")
        self.assertEqual(response2.status, "success")
        self.assertEqual(response1.request_id, "req-iso-1")
        self.assertEqual(response2.request_id, "req-iso-2")
        self.assertEqual(response1.result["content"], "Success 1")
        self.assertEqual(response2.result["content"], "Success 2")

        state1 = self.state_manager.get_state("req-iso-1")
        state2 = self.state_manager.get_state("req-iso-2")
        self.assertEqual(state1.status, "completed")
        self.assertEqual(state2.status, "completed")

        events1 = [e for e in self.event_stream.published_events if e.request_id == "req-iso-1"]
        events2 = [e for e in self.event_stream.published_events if e.request_id == "req-iso-2"]
        self.assertEqual(len(events1), 4) # REQ_REC, EXEC_START, LLM_EXEC, COMPLETED
        self.assertEqual(len(events2), 4)

if __name__ == "__main__":
    unittest.main()
