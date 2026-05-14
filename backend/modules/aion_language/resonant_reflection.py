"""
ResonantReflection - Phase 38B : Intent Reflection Engine
---------------------------------------------------------
Compares resonance fields Ψ1 (input) and Ψ2 (intent/goal)
to quantify understanding and semantic alignment.

Implements the final reflective loop between Aion's
semantic atoms and intrinsic goals - allowing the system
to measure how well its current meaning field aligns with
its internal intent.
"""

import json, math, logging, time
from pathlib import Path
from statistics import mean
from backend.modules.aion_language.resonant_interpreter import RI
from backend.modules.aion_language.language_atom_builder import LAB
from backend.modules.aion_photon.goal_engine import GOALS

logger = logging.getLogger(__name__)
REFLECTION_PATH = Path("data/analysis/resonant_reflection.json")
BASELINE_PATH = Path("data/photon_records/baseline_resonance_field.qphoto")


class ResonantReflection:
    def __init__(self):
        self.last_score = None

    # ─────────────────────────────────────────────
    def compare_fields(self, field_a: dict, field_b: dict):
        """
        Compute semantic alignment between two resonance fields.
        Returns a reflection dict with coherence, overlap, and drift.
        """
        if not field_a or not field_b:
            logger.warning("[Ref] Missing resonance fields for comparison.")
            return None

        # Determine structure type: atoms or clusters
        clusters_a = field_a.get("clusters") or field_a.get("atoms", [])
        clusters_b = field_b.get("clusters") or field_b.get("atoms", [])

        atoms_a = {c.get("center", c.get("lexeme", f"atom:{i}")): c for i, c in enumerate(clusters_a)}
        atoms_b = {c.get("center", c.get("lexeme", f"atom:{i}")): c for i, c in enumerate(clusters_b)}

        shared = set(atoms_a.keys()) & set(atoms_b.keys())
        if not shared:
            return {"semantic_overlap": 0.0, "phase_drift": 1.0, "alignment_score": 0.0}

        overlaps, drifts = [], []
        for k in shared:
            a, b = atoms_a[k], atoms_b[k]
            overlap = min(a.get("link_count", 1), b.get("link_count", 1)) / max(a.get("link_count", 1), b.get("link_count", 1))
            drift = abs(a.get("emotion_bias", 0.5) - b.get("emotion_bias", 0.5)) * 0.5 + \
                    abs(a.get("goal_alignment", 0.0) - b.get("goal_alignment", 0.0)) * 0.5
            overlaps.append(overlap)
            drifts.append(drift)

        reflection = {
            "timestamp": time.time(),
            "semantic_overlap": round(mean(overlaps), 3),
            "phase_drift": round(mean(drifts), 3),
            "alignment_score": round(mean(overlaps) * (1 - mean(drifts)), 3),
            "shared_atoms": list(shared)
        }

        self.last_score = reflection["alignment_score"]
        REFLECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REFLECTION_PATH, "w") as f:
            json.dump(reflection, f, indent=2)

        logger.info(f"[Ref] Alignment={reflection['alignment_score']:.3f} "
                    f"(Overlap={reflection['semantic_overlap']:.3f}, Drift={reflection['phase_drift']:.3f})")
        return reflection

    # ─────────────────────────────────────────────
    def reflect_from_context(self):
        """
        Build a new resonance field (Ψ1) from LAB,
        then compare it either to:
          - a saved baseline resonance field Ψ0, or
          - a synthetic intent field Ψ2 derived from goals.
        """
        input_field = RI.interpret_atoms(LAB.build_atoms())

        # Try to load baseline first
        if BASELINE_PATH.exists():
            try:
                baseline_field = json.load(open(BASELINE_PATH))
                logger.info("[Ref] Comparing current field against baseline resonance field.")
                return self.compare_fields(input_field, baseline_field)
            except Exception as e:
                logger.warning(f"[Ref] Could not load baseline field: {e}")

        # Fallback to goal-derived intent reflection
        if not GOALS or not GOALS.active_goals:
            logger.warning("[Ref] No active goals - using input field only.")
            return input_field

        intent_field = {"clusters": []}
        for g in GOALS.active_goals.values():
            intent_field["clusters"].append({
                "center": f"goal:{g.intent}",
                "link_count": 1,
                "emotion_bias": 0.5,
                "goal_alignment": g.priority
            })

        logger.info("[Ref] Comparing current field against goal-intent field.")
        return self.compare_fields(input_field, intent_field)


# ─────────────────────────────────────────────
# Global instance
# ─────────────────────────────────────────────
try:
    RR
except NameError:
    RR = ResonantReflection()
    print("🪞 ResonantReflection global instance initialized as RR")