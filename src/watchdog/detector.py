from collections import Counter


class Watchdog:
    def __init__(self, repeated_call_threshold=5):
        self.repeated_call_threshold = repeated_call_threshold
        self.tool_history = {}

    def process_event(self, event):
        request_id = event["request_id"]

        if event["event_type"] != "tool_called":
            return None

        tool_name = event["tool_name"]

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
    watchdog = Watchdog()

    events = [
        {
            "request_id": "req-001",
            "event_type": "tool_called",
            "timestamp": 1,
            "tool_name": "search",
            "status": "started"
        },
        {
            "request_id": "req-001",
            "event_type": "tool_called",
            "timestamp": 2,
            "tool_name": "search",
            "status": "started"
        },
        {
            "request_id": "req-001",
            "event_type": "tool_called",
            "timestamp": 3,
            "tool_name": "search",
            "status": "started"
        },
        {
            "request_id": "req-001",
            "event_type": "tool_called",
            "timestamp": 4,
            "tool_name": "search",
            "status": "started"
        },
        {
            "request_id": "req-001",
            "event_type": "tool_called",
            "timestamp": 5,
            "tool_name": "search",
            "status": "started"
        }
    ]

    for event in events:
        alert = watchdog.process_event(event)

        if alert:
            print("ALERT:", alert)


if __name__ == "__main__":
    main()