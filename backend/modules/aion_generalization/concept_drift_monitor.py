#!/usr/bin/env python3
"""
🧠 Concept Drift Monitor — Phase 34: Temporal Stability Feedback
───────────────────────────────────────────────────────────────────────────────
Tracks temporal stability of concept fields (from AKG) by analyzing RSI variance
across recent resonance telemetry. Reinforces stable clusters and decays or
splits unstable ones.

Stable concept = coherent RSI/ε/k pattern over time.
Unstable concept = diverging resonance, potential drift → concept evolution.
"""

import json, time, statistics
from pathlib import Path
from typing import Dict, List, Any
from backend.modules.aion_knowledge import knowledge_graph_core as akg


class ConceptDriftMonitor:
    def __init__(self,
                 stream_path: str = "data/feedback/resonance_stream.jsonl",
                 window: int = 500,
                 stability_threshold: float = 0.05,
                 reinforce_gain: float = 0.02,
                 decay_factor: float = 0.9):
        self.stream_path = Path(stream_path)
        self.window = window
        self.stability_threshold = stability_threshold
        self.reinforce_gain = reinforce_gain
        self.decay_factor = decay_factor

    # ─────────────────────────────────────────────
    def load_stream(self) -> List[Dict[str, Any]]:
        """Load recent resonance telemetry."""
        if not self.stream_path.exists():
            return []
        with open(self.stream_path, "r") as f:
            lines = f.readlines()[-self.window:]
        events = []
        for line in lines:
            try:
                evt = json.loads(line.strip())
                if evt.get("symbol") and evt.get("RSI") is not None:
                    events.append(evt)
            except Exception:
                continue
        return events

    # ─────────────────────────────────────────────
    def compute_stability(self, symbol_events: List[Dict[str, Any]]) -> float:
        """Return RSI variance for a single symbol."""
        rsi_values = [e.get("RSI", 0.0) for e in symbol_events if e.get("RSI") is not None]
        if len(rsi_values) < 2:
            return 0.0
        return statistics.pvariance(rsi_values)

    # ─────────────────────────────────────────────
    def analyze_concepts(self):
        """Evaluate stability for each concept field in AKG."""
        stream = self.load_stream()
        if not stream:
            print("⚠️ No telemetry available for drift analysis.")
            return

        concepts = akg.search(predicate="is_a")
        if not concepts:
            print("⚠️ No concept links found in AKG.")
            return

        concept_map: Dict[str, List[str]] = {}
        for c in concepts:
            subj, obj = c["subject"], c["object"]
            concept_map.setdefault(obj, []).append(subj)

        for concept, members in concept_map.items():
            variances = []
            for m in members:
                symbol = m.replace("symbol:", "")
                symbol_events = [e for e in stream if e.get("symbol") == symbol]
                if not symbol_events:
                    continue
                var = self.compute_stability(symbol_events)
                variances.append(var)
            if not variances:
                continue

            mean_var = statistics.mean(variances)
            print(f"🧭 {concept}: mean RSI variance = {mean_var:.4f}")

            if mean_var < self.stability_threshold:
                # Stable concept → reinforce
                for m in members:
                    akg.reinforce(m, "is_a", concept, gain=self.reinforce_gain)
                print(f"✅ Reinforced stable concept {concept}")
            else:
                # Unstable concept → decay
                self._decay_concept(concept, members, mean_var)

    # ─────────────────────────────────────────────
    def _decay_concept(self, concept: str, members: List[str], var: float):
        """Decay unstable concept field."""
        conn = akg._connect()
        for m in members:
            conn.execute("""
                UPDATE knowledge
                SET strength = strength * ?
                WHERE subject=? AND predicate='is_a' AND object=?
            """, (self.decay_factor, m, concept))
        conn.commit()
        conn.close()
        print(f"⚠️ Decayed unstable concept {concept} (variance={var:.4f})")

    # ─────────────────────────────────────────────
    def run(self):
        print("⏳ Running Concept Drift Monitor…")
        self.analyze_concepts()
        print("✅ Drift analysis complete.")


if __name__ == "__main__":
    monitor = ConceptDriftMonitor()
    monitor.run()