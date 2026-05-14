#!/usr/bin/env python3
"""
🧭 AION Stability Feedback Loop
────────────────────────────────
Monitors resonance telemetry drift and dynamically tunes
Aion learning parameters (ε, confidence slope, neighborhood k)
to maintain coherent stability.
"""

import json
import time
from pathlib import Path
from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry


LOG_PATH = Path("data/telemetry/resonance_stream.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class StabilityFeedbackLoop:
    def __init__(self, epsilon: float = 0.3, k: int = 5):
        self.telemetry = ResonanceTelemetry()
        self.epsilon = epsilon
        self.k = k
        self.last_entropy = 0.0
        self.log_interval = 5  # every N updates
        self.counter = 0

    # ─────────────────────────────────────────────
    # Compute stability entropy
    # ─────────────────────────────────────────────
    def compute_entropy(self, metrics) -> float:
        return abs(metrics["ΔΦ"]) + abs(metrics["Δε"])

    # ─────────────────────────────────────────────
    # Adaptive parameter tuning
    # ─────────────────────────────────────────────
    def adapt(self, entropy: float):
        drift = entropy - self.last_entropy
        # if resonance becoming unstable -> lower exploration
        if drift > 0.002:
            self.epsilon = max(0.05, self.epsilon - 0.01)
            self.k = min(12, self.k + 1)
        else:
            self.epsilon = min(0.6, self.epsilon + 0.01)
            self.k = max(3, self.k - 1)
        self.last_entropy = entropy

    # ─────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────
    def log(self, metrics, entropy):
        record = {
            "timestamp": time.time(),
            "ΔΦ": metrics["ΔΦ"],
            "Δε": metrics["Δε"],
            "μ": metrics["μ"],
            "κ": metrics["κ"],
            "entropy": entropy,
            "ε": self.epsilon,
            "k": self.k,
        }
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")

    # ─────────────────────────────────────────────
    # Step / run loop
    # ─────────────────────────────────────────────
    def step(self):
        metrics = self.telemetry.update()
        entropy = self.compute_entropy(metrics)
        self.adapt(entropy)

        self.counter += 1
        if self.counter % self.log_interval == 0:
            self.log(metrics, entropy)
            self.counter = 0

        return {"entropy": entropy, "ε": self.epsilon, "k": self.k}


if __name__ == "__main__":
    fb = StabilityFeedbackLoop()
    print("🌡 Running Stability Feedback Loop (Ctrl+C to stop)")
    try:
        while True:
            s = fb.step()
            print(f"Δentropy={s['entropy']:.5f} | ε={s['ε']:.2f} | k={s['k']}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n🛑 Stability Feedback stopped.")