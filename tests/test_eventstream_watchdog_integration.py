"""
Integration test: EventStream -> Event.payload -> Watchdog

Proves the Day 2 & Day 6 contracts:
  1. Watchdog subscribes to real EventStream via attach_to_event_stream().
  2. When execution events with ToolResult.to_event_payload() payloads are published,
     the Watchdog receives those payloads automatically through EventStream.publish().
  3. Repeated-tool-call detection fires correctly through the integrated path.
  4. Explicit boundary testing for threshold behavior (no alert before threshold, alert at threshold).
  5. Explicit request isolation testing (separate request_ids do not share counts).
"""

import asyncio
import unittest

from src.events.schema import Event, EventLifecycle
from src.events.stream import EventStream
from src.tools.base import ToolResult
from src.watchdog.detector import Watchdog


class TestEventStreamWatchdogContract(unittest.IsolatedAsyncioTestCase):
    """Verifies the EventStream -> Event.payload -> Watchdog integration seam."""

    def setUp(self):
        self.event_stream = EventStream()
        self.watchdog = Watchdog(repeated_call_threshold=5)
        # Attach Watchdog to the real EventStream using its official attachment method
        self.watchdog.attach_to_event_stream(self.event_stream)

    async def test_real_eventstream_delivery(self):
        """TEST A: Real EventStream Delivery - Verify Watchdog subscribes and receives TOOL_EXECUTION events."""
        tool_result = ToolResult(
            tool_call_id="call_001",
            tool_name="calculator",
            status="completed",
            result={"result": 42},
            execution_time_ms=1.5,
        )
        payload = tool_result.to_event_payload(
            request_id="req-delivery-001", session_id="sess-del-001"
        )

        event = Event(
            event_type=EventLifecycle.TOOL_EXECUTION,
            request_id="req-delivery-001",
            payload=payload,
        )

        # Publish event through real EventStream
        await self.event_stream.publish(event)

        # Verify event was published and stored in stream
        self.assertEqual(len(self.event_stream.published_events), 1)
        stored_event = self.event_stream.published_events[0]
        self.assertEqual(stored_event.event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(stored_event.request_id, "req-delivery-001")

        # Verify Watchdog received and recorded the tool call
        self.assertIn("req-delivery-001", self.watchdog.tool_history)
        self.assertEqual(self.watchdog.tool_history["req-delivery-001"], ["calculator"])
        self.assertEqual(len(self.watchdog.alerts), 0)

    async def test_repeated_tool_detection(self):
        """TEST B: Repeated Tool Detection - Verify repeated events trigger repeated_tool_call alert."""
        tool_result = ToolResult(
            tool_call_id="call_rep",
            tool_name="echo",
            status="completed",
            result={"echo": "test"},
            execution_time_ms=1.0,
        )

        for i in range(5):
            payload = tool_result.to_event_payload(
                request_id="req-repeat-001", session_id="sess-rep"
            )
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.TOOL_EXECUTION,
                    request_id="req-repeat-001",
                    payload=payload,
                )
            )

        # Verify alert was produced inside Watchdog
        self.assertEqual(len(self.watchdog.alerts), 1)
        alert = self.watchdog.alerts[0]
        self.assertEqual(alert["anomaly_type"], "repeated_tool_call")
        self.assertEqual(alert["tool_name"], "echo")
        self.assertEqual(alert["request_id"], "req-repeat-001")
        self.assertEqual(alert["count"], 5)
        self.assertEqual(len(self.event_stream.published_events), 5)

    async def test_threshold_boundary_behavior(self):
        """TEST C: Threshold Boundary Behavior - Verify no alert before threshold, alert at threshold, and configurable threshold."""
        tool_result = ToolResult(
            tool_call_id="call_thresh",
            tool_name="calculator",
            status="completed",
            result={"result": 10},
            execution_time_ms=2.0,
        )

        # Part 1: Default threshold = 5
        # Calls 1 to 4: No alert generated
        for i in range(1, 5):
            payload = tool_result.to_event_payload(
                request_id="req-thresh-5", session_id="sess-t5"
            )
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.TOOL_EXECUTION,
                    request_id="req-thresh-5",
                    payload=payload,
                )
            )
            self.assertEqual(
                len(self.watchdog.alerts),
                0,
                f"No alert should be generated on call {i} (below threshold 5)"
            )

        # Call 5: Alert MUST be generated
        payload = tool_result.to_event_payload(
            request_id="req-thresh-5", session_id="sess-t5"
        )
        await self.event_stream.publish(
            Event(
                event_type=EventLifecycle.TOOL_EXECUTION,
                request_id="req-thresh-5",
                payload=payload,
            )
        )
        self.assertEqual(len(self.watchdog.alerts), 1, "Alert must be generated on call 5 (at threshold)")
        self.assertEqual(self.watchdog.alerts[0]["count"], 5)
        self.assertEqual(self.watchdog.alerts[0]["anomaly_type"], "repeated_tool_call")

        # Part 2: Custom configurable threshold = 3
        custom_stream = EventStream()
        custom_watchdog = Watchdog(repeated_call_threshold=3)
        custom_watchdog.attach_to_event_stream(custom_stream)

        # Calls 1 and 2: No alert
        for i in range(1, 3):
            payload = tool_result.to_event_payload(
                request_id="req-thresh-3", session_id="sess-t3"
            )
            await custom_stream.publish(
                Event(
                    event_type=EventLifecycle.TOOL_EXECUTION,
                    request_id="req-thresh-3",
                    payload=payload,
                )
            )
            self.assertEqual(len(custom_watchdog.alerts), 0, f"No alert on call {i} for threshold 3")

        # Call 3: Alert generated
        payload = tool_result.to_event_payload(
            request_id="req-thresh-3", session_id="sess-t3"
        )
        await custom_stream.publish(
            Event(
                event_type=EventLifecycle.TOOL_EXECUTION,
                request_id="req-thresh-3",
                payload=payload,
            )
        )
        self.assertEqual(len(custom_watchdog.alerts), 1, "Alert generated at call 3 for threshold 3")
        self.assertEqual(custom_watchdog.alerts[0]["count"], 3)

    async def test_request_isolation(self):
        """TEST D: Request Isolation - Verify tool-call counts are strictly isolated by request_id."""
        tool_result = ToolResult(
            tool_call_id="call_iso",
            tool_name="calculator",
            status="completed",
            result={"result": 100},
            execution_time_ms=1.0,
        )

        # 4 calls for Request A
        for _ in range(4):
            payload = tool_result.to_event_payload(
                request_id="req-A", session_id="sess-iso"
            )
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.TOOL_EXECUTION,
                    request_id="req-A",
                    payload=payload,
                )
            )

        # 4 calls for Request B
        for _ in range(4):
            payload = tool_result.to_event_payload(
                request_id="req-B", session_id="sess-iso"
            )
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.TOOL_EXECUTION,
                    request_id="req-B",
                    payload=payload,
                )
            )

        # Total published events = 8, but neither request has reached threshold = 5
        self.assertEqual(len(self.event_stream.published_events), 8)
        self.assertEqual(len(self.watchdog.alerts), 0, "No alerts should fire when both requests are below threshold")
        self.assertEqual(len(self.watchdog.tool_history["req-A"]), 4)
        self.assertEqual(len(self.watchdog.tool_history["req-B"]), 4)

        # 5th call for Request A -> triggers alert ONLY for Request A
        payload_a = tool_result.to_event_payload(
            request_id="req-A", session_id="sess-iso"
        )
        await self.event_stream.publish(
            Event(
                event_type=EventLifecycle.TOOL_EXECUTION,
                request_id="req-A",
                payload=payload_a,
            )
        )
        self.assertEqual(len(self.watchdog.alerts), 1)
        self.assertEqual(self.watchdog.alerts[0]["request_id"], "req-A")
        self.assertEqual(self.watchdog.alerts[0]["count"], 5)

        # Request B still has no alerts
        req_b_alerts = [a for a in self.watchdog.alerts if a["request_id"] == "req-B"]
        self.assertEqual(len(req_b_alerts), 0)

        # 5th call for Request B -> triggers alert for Request B
        payload_b = tool_result.to_event_payload(
            request_id="req-B", session_id="sess-iso"
        )
        await self.event_stream.publish(
            Event(
                event_type=EventLifecycle.TOOL_EXECUTION,
                request_id="req-B",
                payload=payload_b,
            )
        )
        self.assertEqual(len(self.watchdog.alerts), 2)
        self.assertEqual(self.watchdog.alerts[1]["request_id"], "req-B")
        self.assertEqual(self.watchdog.alerts[1]["count"], 5)

    async def test_non_tool_events_do_not_trigger_watchdog(self):
        """Non-TOOL events published to the stream are ignored by the Watchdog."""
        await self.event_stream.publish(
            Event(
                event_type=EventLifecycle.REQUEST_RECEIVED,
                request_id="req-lifecycle-001",
                payload={"session_id": "sess-x", "messages_count": 1},
            )
        )
        await self.event_stream.publish(
            Event(
                event_type=EventLifecycle.COMPLETED,
                request_id="req-lifecycle-001",
                payload={"status": "success"},
            )
        )

        self.assertEqual(len(self.event_stream.published_events), 2)
        self.assertEqual(len(self.watchdog.alerts), 0)
        self.assertEqual(len(self.watchdog.tool_history), 0)

    async def test_multiple_subscribers_receive_same_payload(self):
        """EventStream fan-out: multiple subscribers each receive the same payload."""
        received_a = []
        received_b = []

        stream = EventStream()
        stream.subscribe(lambda p: received_a.append(p))
        stream.subscribe(lambda p: received_b.append(p))

        tool_result = ToolResult(
            tool_call_id="call_fan",
            tool_name="calculator",
            status="completed",
            result={"result": 42},
            execution_time_ms=0.5,
        )
        payload = tool_result.to_event_payload(request_id="req-fan", session_id="")
        await stream.publish(
            Event(
                event_type=EventLifecycle.TOOL_EXECUTION,
                request_id="req-fan",
                payload=payload,
            )
        )

        self.assertEqual(len(received_a), 1)
        self.assertEqual(len(received_b), 1)
        self.assertEqual(received_a[0]["tool_name"], "calculator")
        self.assertEqual(received_b[0]["tool_name"], "calculator")

    async def test_false_positive_normal_sequence_different_tools(self):
        """False Positive Check: Multiple different tools executed in sequence do not trigger alert if each is below threshold."""
        calc_result = ToolResult(
            tool_call_id="call_calc",
            tool_name="calculator",
            status="completed",
            result={"result": 15},
            execution_time_ms=1.2,
        )
        echo_result = ToolResult(
            tool_call_id="call_echo",
            tool_name="echo",
            status="completed",
            result={"echo": "hello"},
            execution_time_ms=0.8,
        )

        request_id = "req-multi-tools"

        # Execute calculator 3 times and echo 2 times (total 5 tool calls across request)
        for i in range(3):
            payload = calc_result.to_event_payload(request_id=request_id, session_id="sess-multi")
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.TOOL_EXECUTION,
                    request_id=request_id,
                    payload=payload,
                )
            )
        for i in range(2):
            payload = echo_result.to_event_payload(request_id=request_id, session_id="sess-multi")
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.TOOL_EXECUTION,
                    request_id=request_id,
                    payload=payload,
                )
            )

        # Total tool events in history = 5, but calculator count is 3 and echo count is 2 (threshold = 5)
        self.assertEqual(len(self.watchdog.tool_history[request_id]), 5)
        self.assertEqual(len(self.watchdog.alerts), 0, "No false positive alert when total calls reach 5 across different tools")

    async def test_false_positive_interleaved_lifecycle_events(self):
        """False Positive Check: Interleaved pipeline lifecycle events do not interfere or cause false alerts."""
        req_id = "req-pipeline-flow"

        # 1. REQUEST_RECEIVED
        await self.event_stream.publish(
            Event(event_type=EventLifecycle.REQUEST_RECEIVED, request_id=req_id, payload={"prompt": "test"})
        )
        # 2. EXECUTION_STARTED
        await self.event_stream.publish(
            Event(event_type=EventLifecycle.EXECUTION_STARTED, request_id=req_id, payload={"provider": "mock"})
        )
        # 3. LLM_EXECUTION
        await self.event_stream.publish(
            Event(event_type=EventLifecycle.LLM_EXECUTION, request_id=req_id, payload={"tokens": 120})
        )
        # 4. TOOL_EXECUTION (calculator #1)
        tool_payload_1 = ToolResult(tool_call_id="c1", tool_name="calculator", status="completed").to_event_payload(req_id)
        await self.event_stream.publish(
            Event(event_type=EventLifecycle.TOOL_EXECUTION, request_id=req_id, payload=tool_payload_1)
        )
        # 5. LLM_EXECUTION
        await self.event_stream.publish(
            Event(event_type=EventLifecycle.LLM_EXECUTION, request_id=req_id, payload={"tokens": 80})
        )
        # 6. TOOL_EXECUTION (echo #1)
        tool_payload_2 = ToolResult(tool_call_id="c2", tool_name="echo", status="completed").to_event_payload(req_id)
        await self.event_stream.publish(
            Event(event_type=EventLifecycle.TOOL_EXECUTION, request_id=req_id, payload=tool_payload_2)
        )
        # 7. COMPLETED
        await self.event_stream.publish(
            Event(event_type=EventLifecycle.COMPLETED, request_id=req_id, payload={"status": "success"})
        )

        self.assertEqual(len(self.event_stream.published_events), 7)
        self.assertEqual(self.watchdog.tool_history[req_id], ["calculator", "echo"])
        self.assertEqual(len(self.watchdog.alerts), 0)

    async def test_false_positive_failed_tool_executions_below_threshold(self):
        """False Positive Check: Failed tool executions below threshold do not trigger false alerts."""
        req_id = "req-failed-tools"
        failed_result = ToolResult(
            tool_call_id="call_fail",
            tool_name="calculator",
            status="failed",
            error="Division by zero",
            execution_time_ms=0.5,
        )

        for _ in range(2):
            payload = failed_result.to_event_payload(request_id=req_id, session_id="sess-fail")
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.TOOL_EXECUTION,
                    request_id=req_id,
                    payload=payload,
                )
            )

        self.assertEqual(len(self.watchdog.tool_history[req_id]), 2)
        self.assertEqual(len(self.watchdog.alerts), 0)


if __name__ == "__main__":
    unittest.main()


