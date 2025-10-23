#!/usr/bin/env python3
"""
🧠 Concept Drift Monitor — Phase 34: Temporal Stability Feedback (Final Closure)
───────────────────────────────────────────────────────────────────────────────
Tracks temporal stability of concept fields (from AKG) by analyzing RSI variance
across recent resonance telemetry. Reinforces stable clusters and decays or
splits unstable ones. Logs all events for meta-learning.

Stable concept = coherent RSI/ε/k pattern over time.
Unstable concept = diverging resonance, potential drift → concept evolution.
"""

import json, time, statistics
from pathlib import Path
from typing import Dict, List, Any
from backend.modules.aion_knowledge import knowledge_graph_core as akg

# ─────────────────────────────────────────────
# Log locations
# ─────────────────────────────────────────────
RSI_LOG = Path("data/feedback/resonance_stream.jsonl")
REINFORCE_LOG = Path("data/feedback/concept_reinforcement.log")


class ConceptDriftMonitor:
    def __init__(self,
                 stream_path: str = "data/feedback/resonance_stream.jsonl",
                 window: int = 500,
                 stability_threshold: float = 0.0025,
                 reinforce_gain: float = 0.02,
                 decay_factor: float = 0.95):
        self.stream_path = Path(stream_path)
        self.window = window
        self.stability_threshold = stability_threshold
        self.reinforce_gain = reinforce_gain
        self.decay_factor = decay_factor

    # ─────────────────────────────────────────────
    def load_stream(self) -> Dict[str, List[float]]:
        """Load recent RSI values per symbol."""
        if not self.stream_path.exists():
            print(f"⚠️ No RSI stream found at {self.stream_path}")
            return {}
        data: Dict[str, List[float]] = {}
        with self.stream_path.open("r") as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    sym, rsi = rec.get("symbol"), rec.get("RSI")
                    if sym and isinstance(rsi, (int, float)):
                        data.setdefault(sym, []).append(rsi)
                except Exception:
                    continue
        # keep only recent window
        for k in list(data.keys()):
            data[k] = data[k][-self.window:]
        return data

    # ─────────────────────────────────────────────
    @staticmethod
    def compute_variance(values: List[float]) -> float:
        """Return population variance for RSI list."""
        if len(values) < 2:
            return None
        return statistics.pvariance(values)

    # ─────────────────────────────────────────────
    def log_event(self, msg: str):
        """Append to reinforcement log."""
        with REINFORCE_LOG.open("a") as f:
            f.write(f"{time.time():.3f} {msg}\n")

    # ─────────────────────────────────────────────
    def analyze_concepts(self):
        """Evaluate RSI stability for each AKG concept."""
        rsi_data = self.load_stream()
        if not rsi_data:
            print("⚠️ No RSI data available for drift analysis.")
            return

        concepts = akg.export_concepts()
        if not concepts:
            print("⚠️ No concepts found in AKG.")
            return

        for cname, members in concepts.items():
            if not members:
                continue

            variances = [
                self.compute_variance(rsi_data.get(sym, []))
                for sym in members
            ]
            variances = [v for v in variances if v is not None]
            if not variances:
                continue

            mean_var = sum(variances) / len(variances)
            print(f"🧭 concept:{cname} → mean RSI variance = {mean_var:.5f}")

            if mean_var < self.stability_threshold:
                # ── Reinforce stable concept
                akg.adjust_concept_strength(cname, +self.reinforce_gain)
                self.log_event(f"reinforce {cname} var={mean_var:.5f}")
                print(f"💪 Reinforced stable {cname} (+{self.reinforce_gain})")
            else:
                # ── Decay unstable concept
                akg.adjust_concept_strength(cname, self.decay_factor, mode="scale")
                self.log_event(f"decay {cname} var={mean_var:.5f}")
                print(f"💤 Decayed unstable {cname} (×{self.decay_factor})")

    # ─────────────────────────────────────────────
    def run(self):
        print("♻️ Running Concept Drift Monitor (Phase 34 Closure)…")
        self.analyze_concepts()
        print("✅ Drift monitoring cycle complete.")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    monitor = ConceptDriftMonitor()
    monitor.run()