"""
ResonantMemoryCache — Phase 39B : Photon Persistence Layer
-----------------------------------------------------------
Caches imported photon–semantic patterns to model resonance persistence
over time.  Each concept λ accumulates frequency, phase, and coherence
history to strengthen long-term semantic stability.
"""

import json, time, logging
from pathlib import Path
from statistics import mean
from backend.modules.aion_knowledge import knowledge_graph_core as akg

logger = logging.getLogger(__name__)
CACHE_PATH = Path("data/memory/resonant_memory_cache.json")


class ResonantMemoryCache:
    def __init__(self):
        self.cache = {}
        self.load()

    # ─────────────────────────────────────────────
    def load(self):
        if CACHE_PATH.exists():
            try:
                self.cache = json.load(open(CACHE_PATH))
                logger.info(f"[RMC] Loaded {len(self.cache)} resonance entries.")
            except Exception as e:
                logger.warning(f"[RMC] Failed to load cache: {e}")
                self.cache = {}

    def save(self):
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        json.dump(self.cache, open(CACHE_PATH, "w"), indent=2)

    # ─────────────────────────────────────────────
    def update_from_photons(self, photons: list):
        """Integrate new photons into persistence cache."""
        now = time.time()
        for p in photons:
            cid = p.get("λ", "unknown")
            entry = self.cache.get(cid, {
                "count": 0, "avg_phase": 0.0, "avg_goal": 0.0,
                "last_seen": 0.0, "coherence": 0.0
            })
            entry["count"] += 1
            entry["avg_phase"] = round((entry["avg_phase"] * (entry["count"] - 1) + p.get("φ", 0.0)) / entry["count"], 3)
            entry["avg_goal"] = round((entry["avg_goal"] * (entry["count"] - 1) + p.get("μ", 0.0)) / entry["count"], 3)
            entry["coherence"] = round(mean([entry["avg_phase"], 1 - abs(0.5 - entry["avg_goal"])]), 3)
            entry["last_seen"] = now
            self.cache[cid] = entry
        self.save()
        logger.info(f"[RMC] Updated cache with {len(photons)} photon entries.")
        return self.cache

    # ─────────────────────────────────────────────
    def reinforce_AKG(self, weight: float = 0.2):
        """Apply persistent reinforcement to AKG based on resonance frequency."""
        for cid, entry in self.cache.items():
            w = min(1.0, weight * entry["coherence"] * entry["count"] / 5)
            akg.add_triplet(cid, "resonance_weight", str(round(w, 3)))
        logger.info(f"[RMC] Reinforced {len(self.cache)} cached concepts in AKG.")


# ─────────────────────────────────────────────
# Global instance
# ─────────────────────────────────────────────
try:
    RMC
except NameError:
    RMC = ResonantMemoryCache()
    print("🌀 ResonantMemoryCache global instance initialized as RMC")