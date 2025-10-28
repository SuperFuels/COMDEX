#!/usr/bin/env python3
# ================================================================
# 🧠 ReflexConsolidationLayer — Phase R8: Cognitive Reflex Atlas
# ================================================================
# Combines ReflexMemory metrics (REI, ΔΦ, Θ) and RuleRecipeEngine
# bundles (ρ, Ī, SQI, domains) into a unified resonance map.
# ================================================================

import json, time, math, logging
from pathlib import Path
from statistics import fmean
from backend.tools.reflex_memory_dashboard import safe_mean
from backend.modules.aion_cognition.rule_recipe_engine import RuleRecipeEngine

logger = logging.getLogger(__name__)
OUT = Path("data/analysis/cognitive_reflex_atlas.json")

class ReflexConsolidationLayer:
    def __init__(self):
        self.recipe_engine = RuleRecipeEngine()
        self.dashboard_path = Path("data/analysis/reflex_memory_dashboard.json")

    # ------------------------------------------------------------
    def load_metrics(self):
        if not self.dashboard_path.exists():
            logger.warning("[ReflexConsolidation] No reflex dashboard found.")
            return {}
        try:
            return json.loads(self.dashboard_path.read_text())
        except Exception:
            return {}

    # ------------------------------------------------------------
    def consolidate(self):
        """Fuse reflex metrics + recipes into Cognitive Reflex Atlas."""
        metrics = self.load_metrics()
        recipes = self.recipe_engine.load_all()

        if not recipes:
            logger.warning("[ReflexConsolidation] No recipes found; cannot build atlas.")
            return {}

        rei = metrics.get("reflex_efficiency_index", 0.5)
        avg_drift = metrics.get("avg_drift", 0.0)
        avg_theta = metrics.get("avg_theta", 1.0)

        atlas_entries = []
        for r in recipes:
            weight = (rei * r.get("SQI", 0.5)) * (1 - abs(r.get("Φ_entropy", 0.5) - r.get("Φ_coherence", 0.5)))
            entry = {
                "domains": r.get("domains", []),
                "hash": r.get("hash"),
                "SQI": r.get("SQI"),
                "Θ_phase": r.get("Θ_phase"),
                "coherence": r.get("Φ_coherence"),
                "entropy": r.get("Φ_entropy"),
                "ΔΦ": r.get("ΔΦ"),
                "weight": round(weight, 3),
                "timestamp": r.get("timestamp"),
            }
            atlas_entries.append(entry)

        # Sort descending by resonance weight
        atlas_entries.sort(key=lambda x: x["weight"], reverse=True)

        atlas_summary = {
            "timestamp": time.time(),
            "reflex_efficiency_index": rei,
            "avg_drift": avg_drift,
            "avg_theta": avg_theta,
            "recipes_linked": len(recipes),
            "entries": atlas_entries[:50],  # top 50 strongest resonant mappings
        }

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(atlas_summary, indent=2))
        logger.info(f"[ReflexConsolidation] Cognitive Reflex Atlas written → {OUT}")
        return atlas_summary