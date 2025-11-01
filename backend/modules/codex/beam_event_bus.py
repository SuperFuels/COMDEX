from __future__ import annotations
# File: backend/modules/codex/beam_event_bus.py
"""
Tessaris * QQC-SLE v0.7
BeamEventBus - unified symbolic/photonic beam event dispatcher.
Bridges symbolic, photonic, holographic, and field-layer telemetry.
"""

from collections import defaultdict
from typing import Callable, Dict, List, Any
import time
import uuid
import logging

logger = logging.getLogger(__name__)

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
            f"{self.source}->{self.target} drift={self.drift:.3f} q={self.qscore:.2f}>"
        )


# ────────────────────────────────────────────────
# 🔁 Pub/Sub System
class BeamEventBus:
    def __init__(self, enable_logging: bool = False):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.enable_logging = enable_logging

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Register callback for a specific event type or '*' for all."""
        self._subscribers[event_type].append(callback)
        if self.enable_logging:
            logger.debug(f"[BeamEventBus] Subscribed to {event_type}: {callback}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Remove a previously registered callback."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                if self.enable_logging:
                    logger.debug(f"[BeamEventBus] Unsubscribed from {event_type}: {callback}")
            except ValueError:
                pass

    def publish(self, event: Union["BeamEvent", str], beam: Optional[Any] = None) -> None:
        """
        Publish either a BeamEvent object or a raw event_type string.

        Safely dispatches to all subscribed listeners, including wildcard ('*') handlers.
        """
        # Normalize input into a BeamEvent instance
        if isinstance(event, str):
            event_obj = BeamEvent(event_type=event, source="system", target="all")
        else:
            event_obj = event

        if self.enable_logging:
            logger.info(f"[BeamEventBus] Emitting {event_obj}")

        # Deliver to specific event-type subscribers
        for cb in self._subscribers.get(event_obj.event_type, []):
            self._safe_invoke(cb, event_obj, beam)

        # Deliver to wildcard ('*') subscribers
        for cb in self._subscribers.get("*", []):
            self._safe_invoke(cb, event_obj, beam)

    def _safe_invoke(self, cb: Callable, event_obj: BeamEvent, beam: Any | None):
        """Invoke callback safely with either one or two args."""
        try:
            if beam is not None:
                cb(event_obj, beam)
            else:
                cb(event_obj)
        except Exception as e:
            logger.warning(f"[BeamEventBus] ❌ Callback failed: {e}")


# ────────────────────────────────────────────────
# 🔗 Singleton instance
beam_event_bus = BeamEventBus()