# ================================================================
# 🛰️ Phase 45G.11 — GHX Telemetry Bridge (ρ∇ψ Enhanced)
# ================================================================
"""
Live telemetry bridge between AION Cognitive Engines and GHX/CodexMetrics.

Streams:
    • Cognitive session metrics (SQI, emotion tone, difficulty)
    • Resonance coherence (ρ), intensity (I), gradient coherence (ρ∇ψ)
    • Adaptive difficulty + emotional trend
    • Real-time bridge to HabitEngine via GHX-Habit subsystem

Outputs:
    data/telemetry/ghx_stream.json   (local mirror for GHXVisualizer)
"""

import json, time, logging
from pathlib import Path
from statistics import mean

logger = logging.getLogger(__name__)

STREAM_PATH = Path("data/telemetry/ghx_stream.json")


# ================================================================
# 🌐 GHXTelemetryBridge
# ================================================================
class GHXTelemetryBridge:
    def __init__(self):
        self.stream = []
        self.last_update = None
        STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    def emit(self, payload: dict):
        """
        Append a new telemetry record to stream.
        Expected fields (any subset allowed):
            SQI, emotion, difficulty, ρ, I, ρ∇ψ, phase
        """
        payload["timestamp"] = time.time()
        self.stream.append(payload)
        self.last_update = payload["timestamp"]
        self._save()
        logger.info(f"[GHX] Emitted telemetry packet → {payload}")

    # ------------------------------------------------------------
    def _save(self):
        """Persist rolling telemetry log."""
        STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)
        out = {
            "timestamp": self.last_update,
            "entries": len(self.stream),
            "stream": self.stream[-300:],  # keep recent 300 events
            "meta": {
                "schema": "GHXTelemetry.v2",
                "desc": "AION→GHX live cognitive telemetry with resonance gradients",
                "fields": [
                    "SQI", "emotion", "difficulty", "ρ", "I", "ρ∇ψ", "phase"
                ],
            },
        }
        json.dump(out, open(STREAM_PATH, "w"), indent=2)

    # ------------------------------------------------------------
    def summarize(self):
        """Aggregate live statistics (SQI + resonance)."""
        if not self.stream:
            return {}

        def avg(key, default=0.0):
            vals = [s.get(key, default) for s in self.stream if s.get(key) is not None]
            return round(mean(vals), 3) if vals else default

        summary = {
            "avg_SQI": avg("SQI"),
            "avg_emotion": avg("emotion", 0.5),
            "avg_difficulty": avg("difficulty", 1.0),
            "avg_coherence": avg("ρ"),
            "avg_intensity": avg("I"),
            "avg_grad_coherence": avg("ρ∇ψ"),
            "total_events": len(self.stream),
            "timestamp": time.time(),
        }

        logger.info(f"[GHX] Live summary → {summary}")
        return summary

    # ------------------------------------------------------------
    def clear(self):
        """Reset the live stream (for new CEE session)."""
        self.stream = []
        self.last_update = None
        if STREAM_PATH.exists():
            STREAM_PATH.unlink()
        logger.info("[GHX] Telemetry stream cleared.")