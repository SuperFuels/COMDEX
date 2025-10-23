#!/usr/bin/env python3
"""
🧬 Concept Evolution Engine — Phase 35: Evolutionary Concept Refinement
───────────────────────────────────────────────────────────────────────────────
Analyzes RSI variance trends across concept fields and evolves the Aion
Knowledge Graph (AKG) structure accordingly:
- Splits unstable concepts into subclusters
- Merges stable, overlapping concepts
- Abstracts reinforced concepts into higher-order meta-concepts
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from sklearn.cluster import KMeans
from backend.modules.aion_knowledge import knowledge_graph_core as akg


class ConceptEvolutionEngine:
    def __init__(self,
                 drift_data_path: str = "data/analysis/concept_field_events.jsonl",
                 stream_path: str = "data/feedback/resonance_stream.jsonl",
                 log_path: str = "data/analysis/concept_evolution.jsonl",
                 split_var_threshold: float = 0.05,
                 merge_rsi_tolerance: float = 0.02,
                 overlap_threshold: float = 0.4):
        self.drift_data_path = Path(drift_data_path)
        self.stream_path = Path(stream_path)
        self.log_path = Path(log_path)
        self.split_var_threshold = split_var_threshold
        self.merge_rsi_tolerance = merge_rsi_tolerance
        self.overlap_threshold = overlap_threshold

    # ─────────────────────────────────────────────
    def load_resonance_stream(self) -> List[Dict[str, Any]]:
        """Load latest resonance stream (symbol, RSI, ε, k)."""
        if not self.stream_path.exists():
            return []
        events = []
        with open(self.stream_path, "r") as f:
            for line in f:
                try:
                    evt = json.loads(line.strip())
                    if evt.get("RSI") is not None and evt.get("symbol") not in (None, "?"):
                        events.append(evt)
                except Exception:
                    continue
        return events

    # ─────────────────────────────────────────────
    def compute_concept_statistics(self, stream: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Aggregate mean RSI and variance per concept."""
        concept_map = akg.export_concepts()  # concept → [symbols]
        stats = {}

        # Normalize symbols in stream
        stream_symbols = []
        for e in stream:
            sym = (
                e.get("symbol")
                or e.get("actual")
                or e.get("predicted_bias")
                or e.get("predicted_temporal")
            )
            if sym:
                stream_symbols.append((str(sym), e.get("RSI", 0.0)))

        print(f"📊 Found {len(concept_map)} concepts, {len(stream_symbols)} symbols in stream.")

        for concept, symbols in concept_map.items():
            rsis = [rsi for (sym, rsi) in stream_symbols if sym in symbols]
            if len(rsis) >= 2:
                stats[concept] = {
                    "mean_RSI": float(np.mean(rsis)),
                    "var_RSI": float(np.var(rsis)),
                    "members": symbols,
                    "n": len(symbols)
                }
                print(f"   {concept}: mean RSI={stats[concept]['mean_RSI']:.3f}, var={stats[concept]['var_RSI']:.5f}, n={len(symbols)}")
            else:
                print(f"   ⚠️ {concept}: insufficient data ({len(rsis)} samples).")
        return stats

    # ─────────────────────────────────────────────
    def split_unstable_concepts(self, concept_stats: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split unstable concepts into new sub-concepts."""
        new_concepts = []
        for concept, data in concept_stats.items():
            if data["var_RSI"] > self.split_var_threshold and len(data["members"]) >= 3:
                print(f"🧩 Splitting unstable concept {concept} (var={data['var_RSI']:.4f})")
                # Simple RSI-based clustering
                X = np.array([[hash(m) % 1000 / 1000.0] for m in data["members"]])
                n_clusters = min(2, len(X))
                kmeans = KMeans(n_clusters=n_clusters, n_init=5, random_state=42)
                labels = kmeans.fit_predict(X)

                for lbl in set(labels):
                    members = [data["members"][i] for i in np.where(labels == lbl)[0]]
                    new_concept = f"{concept}_sub{lbl+1}"
                    new_concepts.append({
                        "type": "split",
                        "parent": concept,
                        "concept": new_concept,
                        "members": members
                    })
                    for m in members:
                        akg.add_triplet(
                            f"symbol:{m}",
                            "is_a",
                            f"concept:{new_concept}",
                            strength=0.1
                        )
                    akg.add_triplet(f"concept:{new_concept}", "derived_from", f"concept:{concept}")
        return new_concepts

    # ─────────────────────────────────────────────
    def merge_stable_concepts(self, concept_stats: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge highly similar, stable concepts."""
        merges = []
        concepts = list(concept_stats.keys())
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                c1, c2 = concepts[i], concepts[j]
                s1, s2 = concept_stats[c1], concept_stats[c2]
                if abs(s1["mean_RSI"] - s2["mean_RSI"]) < self.merge_rsi_tolerance:
                    overlap = len(set(s1["members"]) & set(s2["members"])) / max(len(set(s1["members"] + s2["members"])), 1)
                    if overlap >= self.overlap_threshold:
                        merged = f"{c1}_{c2}_merged"
                        print(f"🔗 Merging {c1} + {c2} → {merged}")
                        all_members = list(set(s1["members"] + s2["members"]))
                        for m in all_members:
                            akg.add_triplet(f"symbol:{m}", "is_a", f"concept:{merged}", strength=0.15)
                        akg.add_triplet(f"concept:{merged}", "superconcept_of", f"concept:{c1}")
                        akg.add_triplet(f"concept:{merged}", "superconcept_of", f"concept:{c2}")
                        merges.append({
                            "type": "merge",
                            "concepts": [c1, c2],
                            "new": merged,
                            "members": all_members
                        })
        return merges

    # ─────────────────────────────────────────────
    def abstract_reinforced_concepts(self, concept_stats: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create higher abstractions for strongly co-reinforced fields."""
        abstractions = []
        stable_concepts = [c for c, d in concept_stats.items() if d["var_RSI"] < self.split_var_threshold / 2]
        if len(stable_concepts) >= 2:
            abstract_name = f"superconcept_{int(time.time())}"
            print(f"🌐 Creating abstraction node: {abstract_name}")
            for c in stable_concepts:
                akg.add_triplet(f"concept:{c}", "subclass_of", f"concept:{abstract_name}")
            abstractions.append({
                "type": "abstract",
                "concepts": stable_concepts,
                "superconcept": abstract_name
            })
        return abstractions

    # ─────────────────────────────────────────────
    def log_events(self, events: List[Dict[str, Any]]):
        """Append evolutionary events to log."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", buffering=1) as f:
            for e in events:
                e["timestamp"] = time.time()
                f.write(json.dumps(e) + "\n")

    # ─────────────────────────────────────────────
    def run(self):
        print("♻️ Running Concept Evolution Engine...")
        stream = self.load_resonance_stream()
        if not stream:
            print("⚠️ No resonance stream found. Aborting evolution cycle.")
            return

        concept_stats = self.compute_concept_statistics(stream)
        if not concept_stats:
            print("⚠️ No concept statistics available. Aborting.")
            return
        
        self.evolve_concepts(concept_stats)

        splits = self.split_unstable_concepts(concept_stats)
        merges = self.merge_stable_concepts(concept_stats)
        abstracts = self.abstract_reinforced_concepts(concept_stats)

        all_events = splits + merges + abstracts
        if all_events:
            self.log_events(all_events)
            print(f"✅ Evolutionary cycle complete: {len(all_events)} structural updates applied.")
        else:
            print("… No evolutionary changes detected this cycle.")

    # ─────────────────────────────────────────────
    # Phase 35.2 – Concept Fusion & Speciation
    # ─────────────────────────────────────────────
    def evolve_concepts(self, concept_stats: dict):
        """Perform fusion, speciation, and reinforcement."""
        if not concept_stats:
            print("⚠️ No concept statistics available for evolution.")
            return

        fused = []
        split = []
        reinforced = []

        # Convert stats to list of tuples for comparison
        items = list(concept_stats.items())

        # ── Fusion pass ──
        for i in range(len(items)):
            ci, si = items[i]
            if si["n"] < 1:
                continue
            for j in range(i + 1, len(items)):
                cj, sj = items[j]
                if sj["n"] < 1:
                    continue

                # Check similarity thresholds
                if abs(si["mean_RSI"] - sj["mean_RSI"]) < 0.02:
                    # Simulate ε/k closeness (placeholder, to be extended)
                    if abs(si.get("mean_eps", 0.28) - sj.get("mean_eps", 0.28)) < 0.01:
                        if abs(si.get("mean_k", 5) - sj.get("mean_k", 5)) <= 1:
                            new_name = f"{ci}_{cj}_fusion"
                            fused.append((ci, cj, new_name))
                            print(f"🧬 Fusing {ci} + {cj} → {new_name}")
                            self.record_evolution_event("fusion", [ci, cj], new_name)

        # ── Speciation pass ──
        for cname, stats in concept_stats.items():
            if stats["n"] > 3 and stats["var_RSI"] > 0.05:
                sub1 = f"{cname}_α"
                sub2 = f"{cname}_β"
                split.append((cname, sub1, sub2))
                print(f"🌱 Speciating {cname} → {sub1}, {sub2}")
                self.record_evolution_event("speciation", [cname], [sub1, sub2])

        # ── Reinforcement pass ──
        for cname, stats in concept_stats.items():
            if stats["var_RSI"] < 0.005 and stats["n"] >= 2:
                reinforced.append(cname)
                print(f"💪 Reinforcing stable concept {cname}")
                self.reinforce_concept(cname, gain=0.01)

        if not (fused or split or reinforced):
            print("… No evolutionary changes detected this cycle.")
        else:
            print(f"✅ Evolutionary cycle complete: "
                  f"{len(fused)} fusions, {len(split)} speciations, {len(reinforced)} reinforcements.")

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────
    def record_evolution_event(self, event_type, sources, result):
        """Log fusion/speciation events for lineage tracking."""
        import json, time
        log_path = Path("data/analysis/concept_evolution_log.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": time.time(),
            "event": event_type,
            "sources": sources,
            "result": result
        }
        with open(log_path, "a", buffering=1) as f:
            f.write(json.dumps(entry) + "\n")

    def reinforce_concept(self, concept, gain=0.01):
        """Reinforce all symbol→concept links in AKG."""
        from backend.modules.aion_knowledge import knowledge_graph_core as akg
        concept_map = akg.export_concepts()
        if concept not in concept_map:
            return
        for sym in concept_map[concept]:
            akg.reinforce(f"symbol:{sym}", "is_a", f"concept:{concept}", gain=gain)


if __name__ == "__main__":
    engine = ConceptEvolutionEngine()
    engine.run()