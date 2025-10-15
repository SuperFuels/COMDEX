"""
Tessaris • QQC–QFC Adapter (πₛ Phase Closure Bridge)
----------------------------------------------------
Bridges Symatics LightWave Engine events (BeamEventBus)
with GHX/QFC visual telemetry channels.

Listens for beam collapse & coherence metrics, and
forwards them to GHXVisualizer (frontend holographic loop).

Implements πₛ closure — completing the feedback
between symbolic, photonic, and holographic layers.
"""

import time
import logging
from collections import deque
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent

logger = logging.getLogger(__name__)


class QQCQFCAdapter:
    """Bridges beam telemetry from LightWave → GHXVisualizer."""

    def __init__(self, max_buffer=128):
        self.metrics_buffer = deque(maxlen=max_buffer)
        self.active = False

    def start(self):
        """Subscribe to BeamEventBus and activate πₛ closure bridge."""
        if self.active:
            logger.warning("[QQCQFCAdapter] Bridge already active.")
            return

        # Subscribe to all event types
        try:
            beam_event_bus.subscribe("*", self._on_event)
        except TypeError:
            # fallback for legacy signature
            beam_event_bus.subscribe(self._on_event)

        self.active = True
        logger.info("[QQCQFCAdapter] 🌐 GHX↔QWave bridge activated (πₛ closure on).")

    def stop(self):
        """Deactivate the feedback bridge."""
        self.active = False
        logger.info("[QQCQFCAdapter] 💤 Bridge deactivated (πₛ closure off).")

    def _on_event(self, event: BeamEvent):
        """Receive BeamEvent and forward to GHX/QFC channel."""
        if not self.active:
            return

        # Collect collapse & coherence telemetry
        payload = {
            "timestamp": time.time(),
            "event_type": event.event_type,
            "source": event.source,
            "target": event.target,
            "drift": getattr(event, "drift", 0.0),
            "qscore": getattr(event, "qscore", 1.0),
            "metadata": event.metadata or {}
        }

        # Cache locally
        self.metrics_buffer.append(payload)

        # Forward to GHX Visualizer / QFC broadcast
        try:
            from backend.modules.ghx.ghx_visualizer import qfc_broadcast_update
            qfc_broadcast_update(payload)
            logger.info(f"[QQCQFCAdapter] 📡 Forwarded event → {event.event_type} | q={payload['qscore']:.2f}")
        except Exception as e:
            logger.warning(f"[QQCQFCAdapter] ⚠️ Broadcast failed: {e}")

    def latest_metrics(self, n=5):
        """Return the most recent n telemetry records."""
        return list(self.metrics_buffer)[-n:]


# ─── Singleton Bridge ─────────────────────────────────────────────
qqc_qfc_adapter = QQCQFCAdapter()