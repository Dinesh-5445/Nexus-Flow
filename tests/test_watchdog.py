"""
Unit tests for the Watchdog Anomaly Detection subsystem.
Validates event format adaptation, repeated tool-call detection,
request isolation, and ToolResult event payload integration.
"""

import unittest
from src.gateway.models import GatewayRequest
from src.gateway.router import GatewayRouter
from src.orchestration.executor import Orchestrator
from src.state.manager import StateManager
from src.events.stream import EventStream
from src.providers.mock_provider import MockProvider
from src.providers.base import LLMResponse, ToolCall
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry
from src.tools.builtin import CalculatorTool
from src.tools.base import ToolResult
from src.watchdog.detector import Watchdog
from src.events.schema import EventLifecycle


class TestWatchdog(unittest.TestCase):

    def setUp(self):
        self.watchdog = Watchdog(repeated_call_threshold=5)

    def test_normal_tool_calls_no_alert(self):
        """A sequence of tool calls below threshold should not trigger an alert."""
        for i in range(1, 5):
            event = {
                "request_id": "req-100",
                "event_type": EventLifecycle.TOOL_EXECUTION.value,
                "timestamp": 1000.0 + i,
                "tool_name": "calculator",
                "status": "completed",
                "session_id": "sess-1",
                "tool_call_id": f"call_{i}",
                "execution_time_ms": 2.5,
                "error": None
            }
            alert = self.watchdog.process_event(event)
            self.assertIsNone(alert)

    def test_repeated_tool_calls_triggers_alert(self):
        """Reaching the repeated call threshold triggers a repeated_tool_call alert."""
        alerts = []
        for i in range(1, 6):
            event = {
                "request_id": "req-200",
                "event_type": EventLifecycle.TOOL_EXECUTION.value,
                "timestamp": 2000.0 + i,
                "tool_name": "echo",
                "status": "completed",
                "session_id": "sess-2",
                "tool_call_id": f"call_{i}",
                "execution_time_ms": 1.0,
                "error": None
            }
            alert = self.watchdog.process_event(event)
            if alert:
                alerts.append(alert)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["request_id"], "req-200")
        self.assertEqual(alerts[0]["anomaly_type"], "repeated_tool_call")
        self.assertEqual(alerts[0]["tool_name"], "echo")
        self.assertEqual(alerts[0]["count"], 5)

    def test_request_isolation(self):
        """Calls from different requests should be tracked independently."""
        # 3 calls for req-A
        for i in range(3):
            self.watchdog.process_event({
                "request_id": "req-A",
                "event_type": EventLifecycle.TOOL_EXECUTION.value,
                "tool_name": "calculator"
            })

        # 3 calls for req-B
        for i in range(3):
            alert = self.watchdog.process_event({
                "request_id": "req-B",
                "event_type": EventLifecycle.TOOL_EXECUTION.value,
                "tool_name": "calculator"
            })
            self.assertIsNone(alert)

        # Neither req-A nor req-B should have triggered an alert (threshold is 5)
        self.assertEqual(len(self.watchdog.tool_history["req-A"]), 3)
        self.assertEqual(len(self.watchdog.tool_history["req-B"]), 3)

    def test_integration_with_tool_result_to_event_payload(self):
        """Events created via ToolResult.to_event_payload are processed correctly."""
        result = ToolResult(
            tool_call_id="call_x",
            tool_name="calculator",
            status="completed",
            result={"result": 42},
            execution_time_ms=3.0
        )

        alerts = []
        for _ in range(5):
            event = result.to_event_payload(request_id="req-integration", session_id="sess-int")
            alert = self.watchdog.process_event(event)
            if alert:
                alerts.append(alert)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["request_id"], "req-integration")
        self.assertEqual(alerts[0]["anomaly_type"], "repeated_tool_call")
        self.assertEqual(alerts[0]["tool_name"], "calculator")
        self.assertEqual(alerts[0]["count"], 5)

    def test_ignore_non_tool_called_events(self):
        """Events that are not tool_called should be ignored."""
        event = {
            "request_id": "req-300",
            "event_type": "request_started",
            "timestamp": 1000.0,
            "session_id": "sess-3"
        }
        alert = self.watchdog.process_event(event)
        self.assertIsNone(alert)
        self.assertNotIn("req-300", self.watchdog.tool_history)


class TestWatchdogRealExecutionIntegration(unittest.IsolatedAsyncioTestCase):
    """
    Integration tests connecting Watchdog to events produced by the actual execution flow:
    GatewayRouter -> Orchestrator -> ToolExecutor -> ToolResult -> EventStream -> Watchdog
    """

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.register(CalculatorTool())
        self.tool_executor = ToolExecutor(registry=self.registry)
        self.mock_provider = MockProvider()
        self.event_stream = EventStream()
        self.state_manager = StateManager()

        self.orchestrator = Orchestrator(
            provider=self.mock_provider,
            tool_executor=self.tool_executor,
            event_stream=self.event_stream
        )

        self.gateway = GatewayRouter(
            orchestrator=self.orchestrator,
            state_manager=self.state_manager,
            event_stream=self.event_stream
        )

        self.watchdog = Watchdog(repeated_call_threshold=5)
        self.watchdog.attach_to_event_stream(self.event_stream)

    async def test_real_execution_event_reaches_watchdog(self):
        """Verify that a tool call in the actual execution flow emits an event received by Watchdog."""
        self.mock_provider.predefined_responses.append(
            LLMResponse(
                content="Calculating...",
                tool_calls=[
                    ToolCall(
                        id="call_real_1",
                        name="calculator",
                        arguments={"expression": "5 + 3"}
                    )
                ]
            )
        )

        request = GatewayRequest(
            request_id="req-real-001",
            session_id="sess-real-001",
            messages=[{"role": "user", "content": "Calculate 5 + 3"}]
        )

        response = await self.gateway.handle_request(request)

        self.assertEqual(response.status, "success")
        self.assertIn("req-real-001", self.watchdog.tool_history)
        self.assertEqual(self.watchdog.tool_history["req-real-001"], ["calculator"])
        self.assertEqual(len(self.watchdog.alerts), 0)

    async def test_normal_execution_flow_no_alert(self):
        """Tool executions below threshold during real execution flow do not trigger an alert."""
        self.mock_provider.predefined_responses.append(
            LLMResponse(
                content="Calculating...",
                tool_calls=[
                    ToolCall(
                        id="call_norm_1",
                        name="calculator",
                        arguments={"expression": "10 + 20"}
                    )
                ]
            )
        )

        request = GatewayRequest(
            request_id="req-norm-001",
            session_id="sess-norm-001",
            messages=[{"role": "user", "content": "Calculate 10 + 20"}]
        )

        await self.gateway.handle_request(request)
        self.assertEqual(len(self.watchdog.alerts), 0)

    async def test_repeated_tool_calls_in_real_execution_triggers_alert(self):
        """Repeated tool calls executed via actual execution flow trigger Watchdog alert at threshold."""
        request_id = "req-repeat-flow"

        for i in range(1, 6):
            self.mock_provider.predefined_responses.append(
                LLMResponse(
                    content=f"Calculating iteration {i}...",
                    tool_calls=[
                        ToolCall(
                            id=f"call_rep_{i}",
                            name="calculator",
                            arguments={"expression": "2 * 2"}
                        )
                    ]
                )
            )

            request = GatewayRequest(
                request_id=request_id,
                session_id="sess-repeat",
                messages=[{"role": "user", "content": "Calculate 2 * 2"}]
            )

            await self.gateway.handle_request(request)

        # 5 calls reached threshold = 5
        self.assertEqual(len(self.watchdog.alerts), 1)
        alert = self.watchdog.alerts[0]
        self.assertEqual(alert["request_id"], request_id)
        self.assertEqual(alert["anomaly_type"], "repeated_tool_call")
        self.assertEqual(alert["tool_name"], "calculator")
        self.assertEqual(alert["count"], 5)

    async def test_request_execution_isolation_in_real_execution(self):
        """Tool calls across different requests in real execution remain isolated."""
        # 3 calls for request A
        for i in range(3):
            self.mock_provider.predefined_responses.append(
                LLMResponse(
                    content="Calc A",
                    tool_calls=[
                        ToolCall(id=f"call_a_{i}", name="calculator", arguments={"expression": "1 + 1"})
                    ]
                )
            )
            await self.gateway.handle_request(
                GatewayRequest(request_id="req-iso-A", messages=[{"role": "user", "content": "1+1"}])
            )

        # 3 calls for request B
        for i in range(3):
            self.mock_provider.predefined_responses.append(
                LLMResponse(
                    content="Calc B",
                    tool_calls=[
                        ToolCall(id=f"call_b_{i}", name="calculator", arguments={"expression": "1 + 1"})
                    ]
                )
            )
            await self.gateway.handle_request(
                GatewayRequest(request_id="req-iso-B", messages=[{"role": "user", "content": "1+1"}])
            )

        # Neither request reached threshold 5
        self.assertEqual(len(self.watchdog.alerts), 0)
        self.assertEqual(len(self.watchdog.tool_history["req-iso-A"]), 3)
        self.assertEqual(len(self.watchdog.tool_history["req-iso-B"]), 3)


if __name__ == "__main__":
    unittest.main()

