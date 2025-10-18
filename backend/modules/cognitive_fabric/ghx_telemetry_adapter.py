# ──────────────────────────────────────────────
#  Tessaris • GHX Telemetry Adapter
#  Stage 13.4 — Live Metrics ↔ GHXVisualizer Stream
#  Streams Φ–ψ resonance and coherence metrics into GHX front-end.
# ──────────────────────────────────────────────

import time
import logging
import threading
from typing import Dict, Any, Optional

from backend.modules.cognitive_fabric.metrics_bridge import CODEX_METRICS

logger = logging.getLogger(__name__)


class GHXTelemetryAdapter:
    """
    Periodically polls CodexMetrics for the latest resonance event
    and pushes formatted telemetry to GHXVisualizer via UCS runtime.
    """

    def __init__(self, poll_interval: float = 5.0):
        self.poll_interval = poll_interval
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.last_timestamp = None

    # ──────────────────────────────────────────────
    #  Public Interface
    # ──────────────────────────────────────────────
    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"[GHXTelemetry] 🩶 started (interval={self.poll_interval}s)")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("[GHXTelemetry] ⏹ stopped")

    # ──────────────────────────────────────────────
    #  Internal Poll Loop
    # ──────────────────────────────────────────────
    def _loop(self):
        while self.running:
            try:
                entry = CODEX_METRICS.latest()
                if not entry:
                    time.sleep(self.poll_interval)
                    continue

                ts = entry.get("timestamp")
                if ts == self.last_timestamp:
                    time.sleep(self.poll_interval)
                    continue
                self.last_timestamp = ts

                payload = {
                    "Φ_mean": entry.get("Φ_mean"),
                    "ψ_mean": entry.get("ψ_mean"),
                    "resonance_index": entry.get("resonance_index"),
                    "coherence_energy": entry.get("coherence_energy"),
                    "timestamp": ts,
                }

                self._emit_to_ghx(payload)

            except Exception as e:
                logger.warning(f"[GHXTelemetry] Poll failed: {e}")
            time.sleep(self.poll_interval)

    # ──────────────────────────────────────────────
    #  Emission into GHXVisualizer
    # ──────────────────────────────────────────────
    def _emit_to_ghx(self, data: Dict[str, Any]):
        """
        Forward telemetry to GHXVisualizer.
        Falls back to console log in dev/test mode.
        """
        try:
            from backend.modules.dimensions.universal_container_system.ucs_runtime import UCSRuntime
            UCSRuntime.broadcast(
                tag="ghx_telemetry_update",
                payload={"type": "resonance", "data": data},
            )
            logger.debug(f"[GHXTelemetry] → GHX broadcast {data}")
        except Exception as e:
            logger.info(f"[GHXTelemetry] (stub) {data} | reason: {e}")


# ──────────────────────────────────────────────
#  Singleton for global runtime
# ──────────────────────────────────────────────
GHX_TELEMETRY = GHXTelemetryAdapter()