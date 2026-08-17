"""
Unit tests for the Watchdog Anomaly Detection subsystem.
Validates event format adaptation, repeated tool-call detection,
request isolation, and ToolResult event payload integration.
"""

import unittest
from src.tools.base import ToolResult
from src.watchdog.detector import Watchdog


class TestWatchdog(unittest.TestCase):

    def setUp(self):
        self.watchdog = Watchdog(repeated_call_threshold=5)

    def test_normal_tool_calls_no_alert(self):
        """A sequence of tool calls below threshold should not trigger an alert."""
        for i in range(1, 5):
            event = {
                "request_id": "req-100",
                "event_type": "tool_called",
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
                "event_type": "tool_called",
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
                "event_type": "tool_called",
                "tool_name": "calculator"
            })

        # 3 calls for req-B
        for i in range(3):
            alert = self.watchdog.process_event({
                "request_id": "req-B",
                "event_type": "tool_called",
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


if __name__ == "__main__":
    unittest.main()
