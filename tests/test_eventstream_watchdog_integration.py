"""
Integration test: EventStream -> Event.payload -> Watchdog

Proves the Day 2 contract:
  1. Watchdog.process_event() is registered as an EventStream subscriber.
  2. When the Orchestrator publishes a TOOL_EXECUTION event with a
     ToolResult.to_event_payload() payload, the Watchdog receives that payload
     automatically through EventStream.publish().
  3. Repeated-tool-call detection fires correctly through the integrated path.

This is NOT a full end-to-end Gateway test (that lives in test_gateway_orchestration.py).
It targets only the EventStream -> Watchdog boundary.
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
        # Connect Watchdog as a subscriber: it receives event.payload dicts.
        self.event_stream.subscribe(self.watchdog.process_event)
        self.alerts: list = []

        # Patch process_event to also collect alerts for assertions.
        original = self.watchdog.process_event

        def capturing_subscriber(payload):
            alert = original(payload)
            if alert:
                self.alerts.append(alert)

        # Replace the default subscription with the capturing wrapper.
        self.event_stream._subscribers = [capturing_subscriber]

    async def test_tool_event_payload_reaches_watchdog(self):
        """A TOOL_EXECUTION event's payload arrives at the Watchdog correctly."""
        tool_result = ToolResult(
            tool_call_id="call_abc",
            tool_name="calculator",
            status="completed",
            result={"result": 8},
            execution_time_ms=2.0,
        )
        payload = tool_result.to_event_payload(
            request_id="req-stream-001", session_id="sess-stream-001"
        )

        event = Event(
            event_type=EventLifecycle.TOOL_EXECUTION,
            request_id="req-stream-001",
            payload=payload,
        )
        await self.event_stream.publish(event)

        # Verify event was stored in the stream.
        self.assertEqual(len(self.event_stream.published_events), 1)
        stored = self.event_stream.published_events[0]
        self.assertEqual(stored.event_type, EventLifecycle.TOOL_EXECUTION)
        self.assertEqual(stored.payload["tool_name"], "calculator")
        self.assertEqual(stored.payload["event_type"], "tool_called")

        # No alert on the first call (threshold = 5).
        self.assertEqual(len(self.alerts), 0)

    async def test_repeated_tool_calls_via_stream_triggers_watchdog_alert(self):
        """Repeated TOOL_EXECUTION events flowing through EventStream trigger Watchdog alert."""
        tool_result = ToolResult(
            tool_call_id="call_rep",
            tool_name="echo",
            status="completed",
            result={"echo": "hello"},
            execution_time_ms=1.0,
        )

        for i in range(5):
            payload = tool_result.to_event_payload(
                request_id="req-repeat-001", session_id="sess-r"
            )
            await self.event_stream.publish(
                Event(
                    event_type=EventLifecycle.TOOL_EXECUTION,
                    request_id="req-repeat-001",
                    payload=payload,
                )
            )

        # Exactly one alert should have fired (on the 5th call).
        self.assertEqual(len(self.alerts), 1)
        alert = self.alerts[0]
        self.assertEqual(alert["anomaly_type"], "repeated_tool_call")
        self.assertEqual(alert["tool_name"], "echo")
        self.assertEqual(alert["request_id"], "req-repeat-001")
        self.assertEqual(alert["count"], 5)

        # All 5 events are stored in the stream.
        self.assertEqual(len(self.event_stream.published_events), 5)

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

        # Both events stored in stream.
        self.assertEqual(len(self.event_stream.published_events), 2)
        # No watchdog alert — non-tool payloads don't have event_type='tool_called'.
        self.assertEqual(len(self.alerts), 0)
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


if __name__ == "__main__":
    unittest.main()
