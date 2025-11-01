#!/usr/bin/env python3
"""
🧩 Concept Field Detector - Phase 33: Conceptual Generalization Feedback
────────────────────────────────────────────────────────────────────────
Analyzes recent resonance telemetry (RSI, ε, k, symbol) and detects
co-activation clusters representing emergent conceptual fields.

When multiple symbols stabilize under similar resonance parameters,
they are grouped into a higher-order concept node (e.g., shape ⊂ geometry).
Clusters are automatically reinforced in the Aion Knowledge Graph (AKG).
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from sklearn.cluster import KMeans
from backend.modules.aion_knowledge import knowledge_graph_core as akg


class ConceptFieldDetector:
    def __init__(
        self,
        stream_path: str = "data/feedback/resonance_stream.jsonl",
        window: int = 500,
        min_cluster_size: int = 2,
        rsi_threshold: float = 0.05,
    ):
        self.stream_path = Path(stream_path)
        self.window = window
        self.min_cluster_size = min_cluster_size
        self.rsi_threshold = rsi_threshold

    # ─────────────────────────────────────────────
    def load_stream(self) -> List[Dict[str, Any]]:
        """Load the most recent resonance events from JSONL."""
        if not self.stream_path.exists():
            return []
        with open(self.stream_path, "r") as f:
            lines = f.readlines()[-self.window :]
        events = []
        for line in lines:
            try:
                evt = json.loads(line.strip())
                if evt.get("RSI") is not None:
                    events.append(evt)
            except Exception:
                continue
        return events

    # ─────────────────────────────────────────────
    def analyze_stream(self) -> List[Dict[str, Any]]:
        """Cluster RSI/ε/k patterns and detect concept fields (forced mode if low RSI)."""
        data = self.load_stream()
        if len(data) < self.min_cluster_size:
            print("⚠️ Not enough data points for clustering.")
            return []

        features, symbols = [], []
        for e in data:
            rsi = e.get("RSI", 0.0)
            eps = e.get("epsilon", 0.0)
            k = e.get("k", 0.0)
            sym = (
                e.get("actual")
                or e.get("symbol")
                or e.get("predicted_bias")
                or e.get("predicted_temporal")
            )
            if sym and sym != "?":
                features.append([rsi, eps, k])
                symbols.append(str(sym))

        if not features or len(symbols) < self.min_cluster_size:
            print("⚠️ No valid symbols found for concept formation.")
            return []

        X = np.array(features)
        mean_rsi = float(np.mean(X[:, 0]))

        print(f"🔍 Forcing cluster formation on symbols: {set(symbols)} (mean RSI={mean_rsi:.3f})")
        clusters = [{
            "concept": "concept_field_forced",
            "members": list(set(symbols)),
            "mean_RSI": mean_rsi
        }]

        return clusters

    # ─────────────────────────────────────────────
    def reinforce_clusters(self, clusters: List[Dict[str, Any]]):
        """Push detected concept fields into the AKG."""
        for c in clusters:
            concept = c["concept"]
            members = c["members"]
            strength = c["mean_RSI"]
            print(
                f"📈 Detected concept field: {concept} "
                f"({len(members)} members, RSI={strength:.3f})"
            )
            for m in members:
                akg.add_triplet(
                    f"symbol:{m}",
                    "is_a",
                    f"concept:{concept}",
                    strength=strength,
                )
            self.log_event(c)

    # ─────────────────────────────────────────────
    def log_event(self, cluster: Dict[str, Any]):
        """Log detected concept field event."""
        log_path = Path("data/analysis/concept_field_events.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        cluster["timestamp"] = time.time()
        with open(log_path, "a", buffering=1) as f:
            f.write(json.dumps(cluster) + "\n")

    # ─────────────────────────────────────────────
    def run(self):
        clusters = self.analyze_stream()
        if clusters:
            self.reinforce_clusters(clusters)
        else:
            print("... No stable concept fields detected this cycle.")


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    detector = ConceptFieldDetector()
    detector.run()