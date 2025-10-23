#!/usr/bin/env python3
"""
🩹 Adaptive Drift Repair Loop
─────────────────────────────
Monitors RSI and triggers self-correction when coherence drops.
Restores stability by damping transitions and resetting predictive bias.
"""

import time
import json
from pathlib import Path


class AdaptiveDriftRepair:
    def __init__(self, log_path: str = "data/feedback/drift_repair.log",
                 threshold: float = 0.6, persist_cycles: int = 3):
        self.threshold = threshold
        self.persist_cycles = persist_cycles
        self.low_counter = 0
        self.last_repair_time = 0.0
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────
    def check_and_repair(self, rsi: float, pb, grad) -> bool:
        """Monitor RSI and trigger repair when drift persists."""
        repaired = False

        if rsi < self.threshold:
            self.low_counter += 1
        else:
            self.low_counter = 0

        # Perform repair if RSI low for N cycles
        if self.low_counter >= self.persist_cycles:
            self.low_counter = 0
            repaired = True
            self.last_repair_time = time.time()

            # ① Dampen unstable transitions
            for k in list(pb.transitions.keys()):
                pb.transitions[k] *= 0.95

            # ② Reset low-confidence paths
            if hasattr(pb, "prediction_confidence"):
                pb.prediction_confidence *= 0.9

            # ③ Normalize ε and k back toward baseline
            pb.epsilon = max(0.1, getattr(pb, "epsilon", 0.2) * 0.95)
            pb.k = max(3, int(getattr(pb, "k", 5) * 0.95))

            # ④ Reduce gradient strength to ease feedback pressure
            if hasattr(grad, "avg_strength"):
                grad.avg_strength *= 0.9

            # ⑤ Log event
            entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "RSI": round(rsi, 4),
                "epsilon": pb.epsilon,
                "k": pb.k,
                "avg_strength": getattr(grad, "avg_strength", 0.0),
            }
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")

            print(f"🩹 Drift repair triggered (RSI ={rsi:.3f}) → reset ε ={pb.epsilon:.2f}, k ={pb.k}")

        return repaired