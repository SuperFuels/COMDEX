"""
Tessaris • QQC–QFC Adapter (πₛ Phase Closure Bridge)
----------------------------------------------------
Bridges Symatics LightWave Engine events (BeamEventBus)
with GHX/QFC visual telemetry channels.

Listens for beam collapse & coherence metrics, and
forwards them to GHX/QFC overlays via GHXVisualBridge.

Implements πₛ closure — completing the feedback
between symbolic, photonic, and holographic layers.
"""

import time
import asyncio
import logging
from collections import deque
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent
from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge

logger = logging.getLogger(__name__)


class QQCQFCAdapter:
    """Bridges beam telemetry from LightWave → GHX/QFC Visualizer."""

    def __init__(self, max_buffer: int = 128):
        self.metrics_buffer = deque(maxlen=max_buffer)
        self.active = False
        self._ghx_bridge = None

    def start(self):
        """Subscribe to BeamEventBus and activate πₛ closure bridge."""
        if self.active:
            logger.warning("[QQCQFCAdapter] Bridge already active.")
            return

        # Subscribe to all beam event types
        try:
            beam_event_bus.subscribe("*", self._on_event)
        except TypeError:
            beam_event_bus.subscribe(self._on_event)

        # Initialize GHX visual bridge (using a temporary resonance ledger)
        try:
            from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger
            ledger = ResonanceLedger()
            self._ghx_bridge = GHXVisualBridge(ledger)
            logger.info("[QQCQFCAdapter] GHXVisualBridge initialized successfully.")
        except Exception as e:
            logger.warning(f"[QQCQFCAdapter] ⚠️ Failed to initialize GHX bridge: {e}")
            self._ghx_bridge = None

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
            "metadata": getattr(event, "metadata", {}) or {}
        }

        # Cache locally
        self.metrics_buffer.append(payload)

        # Forward to GHX/QFC bridge asynchronously
        if self._ghx_bridge:
            try:
                asyncio.create_task(self._ghx_bridge.broadcast_frame())
                logger.info(f"[QQCQFCAdapter] 📡 Forwarded event → {event.event_type} | q={payload['qscore']:.2f}")
            except Exception as e:
                logger.warning(f"[QQCQFCAdapter] ⚠️ Broadcast failed: {e}")
        else:
            logger.debug(f"[QQCQFCAdapter] No GHX bridge available to forward: {event.event_type}")

    def latest_metrics(self, n: int = 5):
        """Return the most recent n telemetry records."""
        return list(self.metrics_buffer)[-n:]


# ─── Singleton Bridge ─────────────────────────────────────────────
qqc_qfc_adapter = QQCQFCAdapter()