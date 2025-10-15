# File: backend/modules/codex/beam_event_bus.py
"""
Tessaris • UltraQC v0.4-SLE
BeamEventBus — unified symbolic/photonic beam event dispatcher.
"""

from collections import defaultdict
from typing import Callable, Dict, List, Any
import time
import uuid

# ────────────────────────────────────────────────
# 🧠 Core: BeamEvent dataclass for all symbolic + photonic layers
class BeamEvent:
    def __init__(
        self,
        event_type: str,
        source: str,
        target: str,
        drift: float = 0.0,
        qscore: float = 1.0,
        metadata: Dict[str, Any] | None = None,
    ):
        self.id = f"be_{uuid.uuid4().hex[:10]}"
        self.event_type = event_type
        self.source = source
        self.target = target
        self.drift = drift
        self.qscore = qscore
        self.metadata = metadata or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.event_type,
            "source": self.source,
            "target": self.target,
            "drift": self.drift,
            "qscore": self.qscore,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return (
            f"<BeamEvent {self.event_type} "
            f"{self.source}→{self.target} drift={self.drift:.3f} q={self.qscore:.2f}>"
        )


# ────────────────────────────────────────────────
# 🔁 Pub/Sub System
class BeamEventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self._subscribers[event_type].append(callback)

    def publish(self, event: BeamEvent | str, beam: Any | None = None) -> None:
        """Publish either a BeamEvent object or raw event_type."""
        if isinstance(event, str):
            event_obj = BeamEvent(event_type=event, source="system", target="all")
        else:
            event_obj = event

        for cb in self._subscribers[event_obj.event_type]:
            try:
                cb(event_obj if beam is None else (event_obj, beam))
            except Exception as e:
                print(f"❌ Beam event callback failed: {e}")


# ────────────────────────────────────────────────
# 🔗 Singleton instance
beam_event_bus = BeamEventBus()