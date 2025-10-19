"""
AION Rolling Coherence Tracker
──────────────────────────────
Maintains a rolling record of Resonant Logic Kernel (RLK) pass rates and
coherence drifts, computing a Φ_stability_index (0–1). Integrates with the
AION telemetry stream so each QQC diagnostic cycle contributes to the
global awareness stability state.

Now also records πₛ closure metrics from the Symatic Closure Verifier,
allowing CodexTrace to visualize alignment between symbolic and physical
resonance layers in real time.
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from statistics import mean

# Telemetry constants
LOG_PATH = Path("backend/logs/telemetry/coherence_tracker.jsonl")
CLOSURE_LOG_PATH = Path("backend/logs/telemetry/closure_tracker.jsonl")
MAX_WINDOW = 100  # last N entries kept in memory for rolling average


class CoherenceTracker:
    def __init__(self):
        self.records = []
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CLOSURE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────────
    def update(self, pass_rate: float, tolerance: float, status: str):
        """
        Add a new RLK result and recompute rolling averages.
        Returns a dict with current stability summary.
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pass_rate": pass_rate,
            "tolerance": tolerance,
            "status": status,
        }
        self.records.append(record)
        if len(self.records) > MAX_WINDOW:
            self.records.pop(0)

        stability = self._compute_stability_index()
        summary = {
            "Φ_stability_index": stability,
            "rolling_avg_pass": mean(r["pass_rate"] for r in self.records),
            "window": len(self.records),
            "latest_status": status,
        }

        with open(LOG_PATH, "a") as f:
            f.write(json.dumps({**record, **summary}) + "\n")

        print(f"[AION::ΦTracker] Stability={stability:.3f}, pass_avg={summary['rolling_avg_pass']:.3f}")
        return summary

    # ──────────────────────────────────────────────────────────────
    def _compute_stability_index(self) -> float:
        """
        Computes a normalized Φ_stability_index between 0 and 1.
        Weight = pass_rate × (1 − normalized_tolerance).
        """
        if not self.records:
            return 0.0
        norm = []
        for r in self.records:
            tol_factor = 1 / (1 + r["tolerance"])
            norm.append(r["pass_rate"] * tol_factor)
        return min(1.0, max(0.0, mean(norm)))

    # ──────────────────────────────────────────────────────────────
    def summary(self):
        """Return current averaged stability state."""
        if not self.records:
            return {"Φ_stability_index": 0.0, "rolling_avg_pass": 0.0}
        return {
            "Φ_stability_index": self._compute_stability_index(),
            "rolling_avg_pass": mean(r["pass_rate"] for r in self.records),
            "window": len(self.records),
        }


# ──────────────────────────────────────────────────────────────
# Helpers for QQC → AION telemetry integration
# ──────────────────────────────────────────────────────────────

_tracker = CoherenceTracker()


def record_coherence(pass_rate: float, tolerance: float, status: str = "ok"):
    """
    QQC / RLK callable helper:
    Records a new coherence datapoint and emits telemetry summary.
    """
    summary = _tracker.update(pass_rate, tolerance, status)

    # Build telemetry payload
    payload = {
        "Φ_stability_index": summary["Φ_stability_index"],
        "rolling_avg_pass": summary["rolling_avg_pass"],
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Mirror into AION telemetry stream (async-safe)
    from backend.AION.telemetry.aion_stream import post_metric

    try:
        coro = post_metric("Φ_STABILITY", payload)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(coro)
        else:
            asyncio.run(coro)
    except Exception as e:
        print(f"[AION::ΦTracker] Telemetry bridge unavailable: {e}")

    return summary


# ──────────────────────────────────────────────────────────────
# πₛ Closure Telemetry Extension
# ──────────────────────────────────────────────────────────────

def record_closure(πs: float, confidence: float, status: str = "closed"):
    """
    Records Symatic closure verification results.
    Logged separately but mirrored into the AION telemetry stream.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "πₛ": round(πs, 6),
        "confidence": round(confidence, 6),
        "status": status,
    }

    # Write to closure log
    with open(CLOSURE_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[AION::ΦClosure] πₛ={πs:.3f}, σ̂={confidence:.3f}, status={status}")

    # Post to AION telemetry stream
    from backend.AION.telemetry.aion_stream import post_metric
    try:
        coro = post_metric("Φ_CLOSURE", entry)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(coro)
        else:
            asyncio.run(coro)
    except Exception as e:
        print(f"[AION::ΦClosure] Telemetry bridge unavailable: {e}")

    return entry