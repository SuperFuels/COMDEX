#!/usr/bin/env python3
# ================================================================
# 🧩 RuleRecipeEngine - Phase R7: Compressed Rule Bundling
# ================================================================
# Generates symbolic rule "recipes" derived from multiple rulebooks.
# Each recipe stores coherence (ρ), entropy (Ī), and SQI weights
# and can be entangled across domains for rapid reuse.
# ================================================================

import json, time, math, hashlib, logging
from pathlib import Path
from statistics import fmean
from typing import Dict, List, Any
from backend.modules.aion_cognition.rulebook_index import RuleBookIndex

logger = logging.getLogger(__name__)
RECIPES_DIR = Path("data/rulebooks/recipes")
RECIPES_DIR.mkdir(parents=True, exist_ok=True)

class RuleRecipeEngine:
    def __init__(self):
        self.index = RuleBookIndex()

    # ------------------------------------------------------------
    def _hash(self, data: Any) -> str:
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]

    def synthesize(self, domains: List[str], phase: float = 1.0) -> Dict[str, Any]:
        """
        Combine multiple rulebooks into a single 'recipe' bundle.
        Weighted averages of coherence (ρ), entropy (Ī), and SQI across rulebooks.
        """
        entries = []
        for d in domains:
            rb = self.index.rulebooks.get(d)
            if not rb: continue
            meta = rb.get("metadata", {})
            coherence = meta.get("Φ_coherence", 0.5)
            entropy = meta.get("Φ_entropy", 0.5)
            sqi = meta.get("SQI", 0.5)
            entries.append((coherence, entropy, sqi))

        if not entries:
            logger.warning(f"[RuleRecipeEngine] No valid rulebooks found for domains {domains}")
            return {}

        rho = fmean([e[0] for e in entries])
        entropy = fmean([e[1] for e in entries])
        sqi = fmean([e[2] for e in entries])
        drift = abs(rho - entropy)

        recipe = {
            "timestamp": time.time(),
            "domains": domains,
            "Θ_phase": round(phase, 3),
            "Φ_coherence": round(rho, 3),
            "Φ_entropy": round(entropy, 3),
            "SQI": round(sqi, 3),
            "ΔΦ": round(drift, 3),
            "entangled_mutations": sum(len(self.index.rulebooks[d].get("mutations", [])) for d in domains if d in self.index.rulebooks),
        }
        recipe["hash"] = self._hash(recipe)

        out_path = RECIPES_DIR / f"recipe_{recipe['hash']}.dc.json"
        with open(out_path, "w") as f:
            json.dump(recipe, f, indent=2)

        logger.info(f"[RuleRecipeEngine] Synthesized recipe for {len(domains)} domains -> {out_path}")
        return recipe

    # ------------------------------------------------------------
    def load_all(self) -> List[Dict[str, Any]]:
        """Load all existing recipes from disk."""
        recipes = []
        for f in RECIPES_DIR.glob("*.dc.json"):
            try:
                recipes.append(json.load(open(f)))
            except Exception:
                continue
        return sorted(recipes, key=lambda r: r.get("timestamp", 0), reverse=True)

    def summarize(self) -> Dict[str, Any]:
        """Return summary of all known recipes."""
        recipes = self.load_all()
        if not recipes:
            return {"count": 0}
        avg_rho = fmean(r["Φ_coherence"] for r in recipes)
        avg_sqi = fmean(r["SQI"] for r in recipes)
        return {
            "count": len(recipes),
            "avg_coherence": round(avg_rho, 3),
            "avg_SQI": round(avg_sqi, 3)
        }

    def load_active_rules(self):
        return []  # placeholder; return current cognitive ruleset later