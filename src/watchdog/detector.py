from collections import Counter
import time
from typing import Any, Dict, Optional


class Watchdog:
    def __init__(self, repeated_call_threshold: int = 5):
        self.repeated_call_threshold = repeated_call_threshold
        self.tool_history = {}

    def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(event, dict):
            return None

        event_type = event.get("event_type")
        if event_type != "tool_called":
            return None

        request_id = event.get("request_id")
        tool_name = event.get("tool_name")

        if not request_id or not tool_name:
            return None

        if request_id not in self.tool_history:
            self.tool_history[request_id] = []

        self.tool_history[request_id].append(tool_name)

        counts = Counter(self.tool_history[request_id])

        if counts[tool_name] >= self.repeated_call_threshold:
            return {
                "request_id": request_id,
                "anomaly_type": "repeated_tool_call",
                "tool_name": tool_name,
                "count": counts[tool_name]
            }

        return None


def main():
    watchdog = Watchdog(repeated_call_threshold=5)

    # Sample events adhering to the shared event payload format (ToolResult.to_event_payload)
    events = [
        {
            "request_id": "req-001",
            "event_type": "tool_called",
            "timestamp": time.time(),
            "tool_name": "calculator",
            "status": "completed",
            "session_id": "sess-abc",
            "tool_call_id": f"call_{i}",
            "execution_time_ms": 1.5,
            "error": None
        }
        for i in range(1, 6)
    ]

    for event in events:
        alert = watchdog.process_event(event)

        if alert:
            print("ALERT:", alert)


if __name__ == "__main__":
    main()