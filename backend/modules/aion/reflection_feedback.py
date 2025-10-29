"""
🧠 Aion Reflection Feedback — PMG Coupling Layer
Computes ΔSQI (coherence shift) and ΔH (entropy shift)
from Photon Memory Grid (PMG) metrics for reflection feedback.
"""

import time
from typing import Dict
from backend.modules.photon_memory.photon_memory_grid import PHOTON_MEMORY_GRID


class ReflectionFeedback:
    def __init__(self):
        self.last_metrics = {"avg_coherence": 0.0, "avg_entropy": 0.0, "timestamp": time.time()}

    def compute_feedback(self) -> Dict[str, float]:
        """Compute photonic deltas since last reflection cycle."""
        metrics = PHOTON_MEMORY_GRID.summarize()
        now = time.time()

        delta_sqi = metrics["avg_coherence"] - self.last_metrics["avg_coherence"]
        delta_h = metrics["avg_entropy"] - self.last_metrics["avg_entropy"]

        feedback = {
            "ΔSQI": round(delta_sqi, 6),
            "ΔH": round(delta_h, 6),
            "avg_coherence": round(metrics["avg_coherence"], 6),
            "avg_entropy": round(metrics["avg_entropy"], 6),
            "timestamp": now,
        }

        self.last_metrics = {**metrics, "timestamp": now}
        return feedback


AION_FEEDBACK = ReflectionFeedback()