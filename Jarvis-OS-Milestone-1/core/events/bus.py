from collections import defaultdict
from collections.abc import Callable
from typing import Any
class EventBus:
    def __init__(self): self._subscribers = defaultdict(list)
    def subscribe(self, event_name: str, handler: Callable[[Any], None]): self._subscribers[event_name].append(handler)
    def publish(self, event_name: str, payload: Any = None):
        for handler in self._subscribers[event_name]: handler(payload)
event_bus = EventBus()
