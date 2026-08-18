"""
Event Stream
Minimal abstraction for publishing events. Foundation for future Pathway integration.

Day 2 contract:
  EventStream stores all published Event objects in-memory (published_events).
  Callers may register payload subscribers via subscribe(). On each publish(),
  the event's .payload dict is forwarded synchronously to every subscriber.
  Watchdog (and future consumers) register here; they receive only Event.payload,
  never the Event envelope — keeping the schema authoritative in schema.py.

Full Pathway integration is intentionally deferred.
"""

from typing import Callable, Dict, Any, List
from .schema import Event


# Type alias: a subscriber receives an Event payload dict and returns anything (ignored).
PayloadSubscriber = Callable[[Dict[str, Any]], Any]


class EventStream:
    """
    In-memory event stream for Day 2 to simulate Pathway publish capability.

    Integration seam:
        EventStream.publish(event)
            -> stores event in published_events
            -> calls each subscriber with event.payload
    """

    def __init__(self):
        self.published_events: List[Event] = []
        self._subscribers: List[PayloadSubscriber] = []

    def subscribe(self, subscriber: PayloadSubscriber) -> None:
        """
        Register a callable that will be called with Event.payload on every publish.

        The subscriber is responsible for inspecting the payload and deciding
        whether to act on it (e.g. Watchdog checks payload['event_type']).
        """
        self._subscribers.append(subscriber)

    async def publish(self, event: Event) -> None:
        """
        Publishes an event to the stream.
        - Stores the full Event in published_events (for inspection / REST transport).
        - Dispatches event.payload to each registered subscriber.
        """
        self.published_events.append(event)
        for subscriber in self._subscribers:
            subscriber(event.payload)
        # In a real implementation, this would send to Pathway or Kafka
