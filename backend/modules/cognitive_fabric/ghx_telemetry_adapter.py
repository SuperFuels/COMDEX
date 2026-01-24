# ──────────────────────────────────────────────
#  Tessaris * GHX Telemetry Adapter
#  Stage 13.4 -> 13.5 - Live Metrics ↔ GHXVisualizer + MorphicLedger
#  Streams Φ-ψ resonance and coherence metrics into GHX front-end
#  and appends to rqc_live_telemetry.jsonl for WS/SSE feeds.
# ──────────────────────────────────────────────

import os
import time
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional

from backend.modules.cognitive_fabric.metrics_bridge import CODEX_METRICS

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Ledger path resolution (stable + env override + prefer runtime truth feed)
# -----------------------------------------------------------------------------

def _resolve_rqc_ledger_path() -> Path:
    """
    Resolution order:
      1) RQC_LEDGER_PATH (absolute/relative full path)
      2) RQC_LEDGER_FILE:
           - if contains a slash => treat as full path
           - else => join with RQC_LEDGER_DIR (default data/ledger)
      3) Prefer runtime truth feed if present:
           .runtime/COMDEX_MOVE/data/ledger/rqc_live_telemetry.jsonl
      4) Fallback:
           data/ledger/rqc_live_telemetry.jsonl
    """
    p = (os.getenv("RQC_LEDGER_PATH") or "").strip()
    if p:
        return Path(p)

    f = (os.getenv("RQC_LEDGER_FILE") or "").strip()
    d = (os.getenv("RQC_LEDGER_DIR") or "data/ledger").strip()

    if f:
        if "/" in f or "\\" in f:
            return Path(f)
        return Path(d) / f

    runtime = Path(".runtime") / "COMDEX_MOVE" / "data" / "ledger" / "rqc_live_telemetry.jsonl"
    root = Path("data") / "ledger" / "rqc_live_telemetry.jsonl"
    return runtime if runtime.exists() else root


LEDGER_PATH = str(_resolve_rqc_ledger_path())


class GHXTelemetryAdapter:
    """
    Periodically polls CodexMetrics for the latest resonance event,
    broadcasts formatted telemetry to GHXVisualizer via UCS runtime,
    and persists snapshots to the RQC telemetry JSONL ledger.
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
        # hard guard in case startup hooks fire twice
        if self._thread and self._thread.is_alive():
            self.running = True
            return

        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"[GHXTelemetry] 🩶 started (interval={self.poll_interval}s, ledger={LEDGER_PATH})")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("[GHXTelemetry] ⏹ stopped")

    def latest_payload(self) -> Dict[str, Any]:
        """
        Return most recent Φ-ψ-κ-T telemetry packet.
        Falls back to last ledger entry or stub.
        """
        if self._latest:
            return self._latest

        # fallback: last line from ledger (bounded read)
        if os.path.exists(LEDGER_PATH):
            try:
                with open(LEDGER_PATH, "rb") as f:
                    try:
                        f.seek(-4096, os.SEEK_END)
                    except OSError:
                        f.seek(0)
                    tail = f.read().decode("utf-8", errors="ignore")
                lines = [ln for ln in tail.splitlines() if ln.strip()]
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

                ts = entry.get("timestamp") or time.time()

                # Avoid re-writing the same snapshot
                if ts == self.last_timestamp:
                    time.sleep(self.poll_interval)
                    continue
                self.last_timestamp = ts

                # CODEX_METRICS.record_event() often stores the user payload under "payload"
                inner = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}

                # prefer values from inner first (that’s where record_event puts them)
                def pick(*keys, default=None):
                    for k in keys:
                        v = inner.get(k) if isinstance(inner, dict) else None
                        if v is None:
                            v = entry.get(k)
                        if v is not None:
                            return v
                    return default

                payload = {
                    "timestamp": ts,
                    "operator": entry.get("event") or inner.get("operator") or "unknown",
                    "event": entry.get("event", "resonance_update"),

                    "Φ_mean": pick("Φ_mean", "phi", "Φ"),
                    "ψ_mean": pick("ψ_mean", "psi", "ψ"),
                    "resonance_index": pick("resonance_index"),
                    "coherence_energy": pick("coherence_energy"),
                    "entanglement_fidelity": pick("entanglement_fidelity"),
                    "mutual_coherence": pick("mutual_coherence"),
                    "phase_correlation": pick("phase_correlation"),

                    "gain": pick("gain"),
                    "closure_state": pick("closure_state"),
                    "phi_dot": pick("phi_dot"),

                    "κ": pick("κ", "kappa", default=0.0),
                    "T": pick("T", default=0.0),
                }

                # IMPORTANT: if this event contains no metrics, don't write it to the ledger
                if payload["Φ_mean"] is None and payload["ψ_mean"] is None and payload["resonance_index"] is None:
                    time.sleep(self.poll_interval)
                    continue

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
        """Append payload to the RQC telemetry JSONL ledger."""
        try:
            Path(LEDGER_PATH).parent.mkdir(parents=True, exist_ok=True)
            with open(LEDGER_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
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
            logger.debug(f"[GHXTelemetry] -> GHX broadcast {data}")
        except Exception as e:
            logger.info(f"[GHXTelemetry] (stub) {data} | reason: {e}")


# ──────────────────────────────────────────────
#  Singleton for global runtime
# ──────────────────────────────────────────────
GHX_TELEMETRY = GHXTelemetryAdapter()