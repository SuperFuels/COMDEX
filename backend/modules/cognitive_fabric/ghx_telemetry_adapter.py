# ──────────────────────────────────────────────
#  Tessaris • GHX Telemetry Adapter
#  Stage 13.4 → 13.5 — Live Metrics ↔ GHXVisualizer + MorphicLedger
#  Streams Φ–ψ resonance and coherence metrics into GHX front-end
#  and appends to data/ledger/rqc_live_telemetry.jsonl for SSE feeds.
# ──────────────────────────────────────────────

import os
import time
import json
import logging
import threading
from typing import Dict, Any, Optional

from backend.modules.cognitive_fabric.metrics_bridge import CODEX_METRICS

logger = logging.getLogger(__name__)

LEDGER_PATH = "data/ledger/rqc_live_telemetry.jsonl"


class GHXTelemetryAdapter:
    """
    Periodically polls CodexMetrics for the latest resonance event,
    broadcasts formatted telemetry to GHXVisualizer via UCS runtime,
    and persists snapshots to the MorphicLedger JSONL file.
    """

    def __init__(self, poll_interval: float = 5.0):
        self.poll_interval = poll_interval
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.last_timestamp = None
        self._latest: Dict[str, Any] = {}

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

    def latest_payload(self) -> Dict[str, Any]:
        """
        Return most recent Φ–ψ–κ–T telemetry packet.
        Falls back to last ledger entry or stub.
        """
        if self._latest:
            return self._latest

        # fallback: last line from ledger
        if os.path.exists(LEDGER_PATH):
            try:
                with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        self._latest = json.loads(lines[-1])
                        return self._latest
            except Exception as e:
                logger.warning(f"[GHXTelemetry] ledger read fail: {e}")

        # stub
        return {
            "timestamp": time.time(),
            "Φ_mean": 1.0,
            "ψ_mean": 1.0,
            "resonance_index": 1.0,
            "coherence_energy": 1.0,
            "κ": 0.0,
            "T": 0.0,
            "event": "telemetry_stub",
        }

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
                    "timestamp": ts,
                    "Φ_mean": entry.get("Φ_mean"),
                    "ψ_mean": entry.get("ψ_mean"),
                    "resonance_index": entry.get("resonance_index"),
                    "coherence_energy": entry.get("coherence_energy"),
                    "κ": entry.get("payload", {}).get("κ", 0.0),
                    "T": entry.get("payload", {}).get("T", 0.0),
                    "event": entry.get("event", "resonance_update"),
                }

                self._latest = payload
                self._write_ledger(payload)
                self._emit_to_ghx(payload)

            except Exception as e:
                logger.warning(f"[GHXTelemetry] Poll failed: {e}")
            time.sleep(self.poll_interval)

    # ──────────────────────────────────────────────
    #  Ledger Writer
    # ──────────────────────────────────────────────
    def _write_ledger(self, payload: dict):
        """Append payload to the MorphicLedger JSONL."""
        try:
            os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
            with open(LEDGER_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as e:
            logger.warning(f"[GHXTelemetry] Ledger write failed: {e}")

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