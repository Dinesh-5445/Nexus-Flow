"""
Event Stream
Minimal abstraction for publishing events. Foundation for future Pathway integration.
"""

from typing import List
from .schema import Event


class EventStream:
    """
    In-memory event stream for Day 2 to simulate Pathway publish capability.
    """
    def __init__(self):
        self.published_events: List[Event] = []

    async def publish(self, event: Event) -> None:
        """
        Publishes an event to the stream.
        """
        self.published_events.append(event)
        # In a real implementation, this would send to Pathway or Kafka
        # print(f"[EventStream] Published: {event.event_type.value} for {event.request_id}")
