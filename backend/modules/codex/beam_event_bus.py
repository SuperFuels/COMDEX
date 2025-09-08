# File: backend/modules/codex/beam_event_bus.py

"""
beam_event_bus.py

Simple pub/sub system to enable symbolic beam lifecycle broadcasts.
"""

from collections import defaultdict
from typing import Callable, Dict, List

class BeamEventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, beam) -> None:
        for cb in self._subscribers[event_type]:
            try:
                cb(beam)
            except Exception as e:
                print(f"❌ Beam event callback failed: {e}")

beam_event_bus = BeamEventBus()