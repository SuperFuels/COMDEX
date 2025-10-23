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
import uuid, time
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from sklearn.cluster import KMeans
from backend.modules.aion_knowledge import knowledge_graph_core as akg
from backend.modules.aion_knowledge import knowledge_graph_core as akg

# --- TEMPORARY TEST LINKING ---
from backend.modules.aion_knowledge import knowledge_graph_core as akg
akg.add_triplet("symbol:ψ", "is_a", "concept:concept_field_1")
akg.add_triplet("symbol:γ", "is_a", "concept:concept_field_3")

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
        """Split unstable concepts into new sub-concepts (auto-AKG node creation)."""
        new_concepts = []

        for concept, data in concept_stats.items():
            # Split only if unstable and has sufficient members
            if data["var_RSI"] > self.split_var_threshold and len(data["members"]) >= 3:
                print(f"🧩 Splitting unstable concept {concept} (var={data['var_RSI']:.4f})")

                # RSI-based clustering (placeholder heuristic)
                X = np.array([[hash(m) % 1000 / 1000.0] for m in data["members"]])
                n_clusters = min(2, len(X))
                kmeans = KMeans(n_clusters=n_clusters, n_init=5, random_state=42)
                labels = kmeans.fit_predict(X)

                for lbl in set(labels):
                    members = [data["members"][i] for i in np.where(labels == lbl)[0]]
                    new_concept = f"{concept}_sub{lbl+1}"

                    # Auto-create the new concept node in AKG
                    meta = {
                        "origin": "speciation",
                        "parent": concept,
                        "timestamp": time.time(),
                        "rsi_mean": round(np.mean([data["mean_RSI"]]), 4),
                        "rsi_var": round(data["var_RSI"], 5),
                        "cluster_id": int(lbl)
                    }

                    try:
                        new_id = akg.create_concept_node(
                            name=new_concept,
                            symbols=members,
                            meta=meta
                        )
                        print(f"🌱 Created new sub-concept node: {new_concept} [{new_id}]")
                    except Exception as e:
                        print(f"⚠️ Failed to create sub-concept node {new_concept}: {e}")
                        continue

                    # Maintain graph lineage
                    akg.add_triplet(f"concept:{new_concept}", "derived_from", f"concept:{concept}")

                    new_concepts.append({
                        "type": "split",
                        "parent": concept,
                        "concept": new_concept,
                        "members": members,
                        "meta": meta
                    })

        return new_concepts

    # ─────────────────────────────────────────────
    def merge_stable_concepts(self, concept_stats: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge highly similar, stable concepts."""
        import sys
        from backend.modules.aion_knowledge import knowledge_graph_core as akg

        # 🧱 Corrected Cooldown Guard — check AKG module directly
        akg_mod = sys.modules.get("backend.modules.aion_knowledge.knowledge_graph_core")
        if getattr(akg_mod, "disable_auto_merge", False):
            print("🚫 Auto-merge suppressed — AKG cooldown active (checked module directly).")
            return []

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
        """Perform fusion, speciation, and reinforcement (stabilized)."""
        if not concept_stats:
            print("⚠️ No concept statistics available for evolution.")
            return

        import json, time, numpy as np
        from pathlib import Path

        fused, split, reinforced = [], [], []

        # Convert stats to list for iteration
        items = list(concept_stats.items())

        # ── Dynamic fusion threshold ──
        FUSION_PARAM = Path("data/feedback/fusion_threshold.json")
        if FUSION_PARAM.exists():
            try:
                with FUSION_PARAM.open() as f:
                    cfg = json.load(f)
                    DYNAMIC_THRESHOLD = cfg.get("adjusted_fusion_threshold", 0.02)
                print(f"⚙️  Loaded adaptive fusion threshold = {DYNAMIC_THRESHOLD:.4f}")
            except Exception as e:
                print(f"⚠️  Could not load fusion threshold: {e}")
                DYNAMIC_THRESHOLD = 0.02
        else:
            DYNAMIC_THRESHOLD = 0.02
            print("⚠️  No fusion threshold file found; using default 0.02")

        # ── Limits ──
        fusion_count = 0
        MAX_FUSIONS_PER_CYCLE = 10
        MAX_TOTAL_FUSIONS = 20

        # ── Fusion pass ──
        for i, (ci, si) in enumerate(items):
            if si["n"] < 1:
                continue
            for j in range(i + 1, len(items)):
                cj, sj = items[j]
                if sj["n"] < 1:
                    continue

                # Stop conditions
                if fusion_count >= MAX_FUSIONS_PER_CYCLE:
                    print("⚖️ Fusion limit reached; stopping this cycle.")
                    print("🕒 Cooling down fusion engine for 3 s…")
                    time.sleep(3)

                    # ── Post-fusion merge suppression ──
                    print("🧱  Suppressing downstream merges — cooldown in effect.")
                    try:
                        akg.start_auto_merge_cooldown(60)
                    except Exception:
                        pass

                    return  # hard stop — prevents downstream merges

                if any(sub in ci for sub in ["_fusion_", "_merged"]) or any(sub in cj for sub in ["_fusion_", "_merged"]):
                    continue

                # Adaptive RSI check
                if abs(si["mean_RSI"] - sj["mean_RSI"]) < DYNAMIC_THRESHOLD:
                    if abs(si.get("mean_eps", 0.28) - sj.get("mean_eps", 0.28)) < 0.01:
                        if abs(si.get("mean_k", 5) - sj.get("mean_k", 5)) <= 1:
                            new_name = f"{ci}_{cj}_fusion"
                            fused_symbols = sorted(list(set(si["members"]) | set(sj["members"])))
                            stat = {
                                "mean": np.mean([si["mean_RSI"], sj["mean_RSI"]]),
                                "var": np.mean([si["var_RSI"], sj["var_RSI"]]),
                            }
                            print(f"🧬 Fusing {ci} + {cj} → {new_name}")

                            try:
                                new_id = akg.create_concept_node(
                                    name=new_name,
                                    symbols=fused_symbols,
                                    meta={
                                        "origin": "fusion",
                                        "parents": [ci, cj],
                                        "rsi_mean": round(stat["mean"], 4),
                                        "rsi_var": round(stat["var"], 4),
                                        "timestamp": time.time(),
                                        "status": "active",
                                    },
                                )
                                print(f"🌐 Created fused node: {new_name} [{new_id}]")
                            except Exception as e:
                                print(f"⚠️ Fusion node creation failed: {e}")
                                continue

                            # Add links + reinforce
                            for m in fused_symbols:
                                akg.add_triplet(f"symbol:{m}", "is_a", f"concept:{new_name}", strength=0.15)
                            akg.add_triplet(f"concept:{new_name}", "derived_from", f"concept:{ci}", strength=1.0)
                            akg.add_triplet(f"concept:{new_name}", "derived_from", f"concept:{cj}", strength=1.0)
                            fused.append((ci, cj, new_name))
                            self.record_evolution_event("fusion", [ci, cj], new_name)
                            self.reinforce_concept(new_name, gain=0.002)

                            fusion_count += 1
                            if fusion_count > MAX_TOTAL_FUSIONS:
                                print("🧯 Fusion runaway detected — aborting evolution cycle for safety.")
                                print("🕒 Cooling down fusion engine for 5 s…")

                                # ── Post-fusion merge suppression ──
                                print("🧱  Suppressing downstream merges — cooldown in effect.")
                                try:
                                    akg.start_auto_merge_cooldown(60)
                                except Exception:
                                    pass

                                time.sleep(5)
                                return

        # ── Speciation pass ──
        for cname, stats in concept_stats.items():
            if stats["n"] > 3 and stats["var_RSI"] > 0.05:
                sub1, sub2 = f"{cname}_α", f"{cname}_β"
                split.append((cname, sub1, sub2))
                print(f"🌱 Speciating {cname} → {sub1}, {sub2}")
                self.record_evolution_event("speciation", [cname], [sub1, sub2])

        # ── Reinforcement pass ──
        for cname, stats in concept_stats.items():
            if stats["var_RSI"] < 0.005 and stats["n"] >= 2:
                reinforced.append(cname)
                print(f"💪 Reinforcing stable concept {cname}")
                self.reinforce_concept(cname, gain=0.01)

        # ── Summary ──
        if not (fused or split or reinforced):
            print("… No evolutionary changes detected this cycle.")
        else:
            print(f"✅ Evolutionary cycle complete: "
                  f"{len(fused)} fusions, {len(split)} speciations, {len(reinforced)} reinforcements.")

    def register_new_concept(concept_name, symbols, rsi_mean, rsi_var, parents, origin):
        meta = {
            "timestamp": time.time(),
            "rsi_mean": rsi_mean,
            "rsi_var": rsi_var,
            "parents": parents,
            "origin": origin,              # "fusion" | "speciation"
            "status": "active"
        }
        node_id = akg.create_concept_node(
            name=concept_name,
            symbols=symbols,
            meta=meta
        )
        print(f"[Evolution] Created new concept node → {concept_name} ({origin}) [{node_id}]")
        return node_id

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