# ================================================================
# 🧠 Phase 45F.8 — Semantic Memory Stabilization (Resonant Memory Cache)
# ================================================================
"""
Extends the Phase 39B Photon Persistence Layer into a unified
Resonant Memory Cache (RMC) that supports both photon-based and
lexical-semantic persistence.

It now stores stabilized Φ–ψ–η–Λ tensors derived from the LangField
resonance pipeline and applies long-term stability decay to model
semantic drift over time.

Inputs:
    data/qtensor/langfield_resonance_adapted.qdata.json
Outputs:
    data/memory/resonant_memory_cache.json
"""

import json, time, logging
from pathlib import Path
from statistics import mean

# Optional — reinforcement hook
try:
    from backend.modules.aion_knowledge import knowledge_graph_core as akg
except Exception:
    akg = None

logger = logging.getLogger(__name__)

ADAPTED_QTENSOR_PATH = Path("data/qtensor/langfield_resonance_adapted.qdata.json")
CACHE_PATH = Path("data/memory/resonant_memory_cache.json")


class ResonantMemoryCache:
    def __init__(self):
        self.cache = {}   # photon+semantic combined memory
        self.last_update = None
        self.load()

    # ------------------------------------------------------------
    def load(self):
        """Load existing cache from disk if present."""
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

    # ------------------------------------------------------------
    # 🌊 Phase 39B — Photon Integration Layer
    # ------------------------------------------------------------
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
            entry["avg_phase"] = round(
                (entry["avg_phase"] * (entry["count"] - 1) + p.get("φ", 0.0)) / entry["count"], 3
            )
            entry["avg_goal"] = round(
                (entry["avg_goal"] * (entry["count"] - 1) + p.get("μ", 0.0)) / entry["count"], 3
            )
            entry["coherence"] = round(
                mean([entry["avg_phase"], 1 - abs(0.5 - entry["avg_goal"])]), 3
            )
            entry["last_seen"] = now
            self.cache[cid] = entry
        self.save()
        logger.info(f"[RMC] Updated cache with {len(photons)} photon entries.")
        return self.cache

    def reinforce_AKG(self, weight: float = 0.2):
        """Apply persistent reinforcement to AKG based on resonance frequency."""
        if not akg:
            logger.warning("[RMC] AKG reinforcement skipped (module not loaded).")
            return
        for cid, entry in self.cache.items():
            w = min(1.0, weight * entry.get("coherence", 0.5) * entry.get("count", 1) / 5)
            akg.add_triplet(cid, "resonance_weight", str(round(w, 3)))
        logger.info(f"[RMC] Reinforced {len(self.cache)} cached concepts in AKG.")

    # ------------------------------------------------------------
    # 🧠 Phase 45F.8 — Semantic Tensor Layer
    # ------------------------------------------------------------
    def _safe_load(self, path: Path):
        if not path.exists():
            logger.warning(f"[RMC] Missing file: {path}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def ingest_tensors(self):
        """Load adapted QTensor and merge into memory cache."""
        data = self._safe_load(ADAPTED_QTENSOR_PATH)
        tensor = data.get("tensor_field", {})
        if not tensor:
            logger.warning("[RMC] No tensor data found to ingest.")
            return

        timestamp = time.time()
        for wid, t in tensor.items():
            self.cache[wid] = {
                "Φ": t.get("Φ", 1.0),
                "ψ": t.get("ψ", 1.0),
                "η": t.get("η", 1.0),
                "Λ": t.get("Λ", 1.0),
                "q_val": t.get("q_val", 1.0),
                "phase": t.get("phase", 0.0),
                "stability": 1.0,
                "last_update": timestamp,
            }
        self.last_update = timestamp
        logger.info(f"[RMC] Ingested {len(tensor)} tensor entries into cache.")
        self.save()

    def stabilize(self, decay_rate: float = 0.001):
        """Apply slow decay to simulate semantic drift stabilization."""
        if not self.cache:
            logger.warning("[RMC] No memory to stabilize.")
            return
        for wid, m in self.cache.items():
            if "stability" in m:
                m["stability"] = round(m["stability"] * (1 - decay_rate), 6)
        logger.info(f"[RMC] Applied stability decay: rate={decay_rate}")
        self.save()

    def recall(self, wid: str):
        """Retrieve stabilized tensor or photon entry for given id."""
        return self.cache.get(wid.lower(), None)

    # ------------------------------------------------------------
    def export(self):
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": self.last_update,
                "entries": len(self.cache),
                "cache": self.cache,
                "meta": {
                    "schema": "ResonantMemoryCache.v2",
                    "desc": "Unified photon + semantic Φ–ψ–η–Λ resonance cache"
                }
            }, f, indent=2)
        logger.info(f"[RMC] Exported unified cache → {CACHE_PATH}")


# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    rmc = ResonantMemoryCache()
    rmc.ingest_tensors()
    rmc.stabilize(decay_rate=0.001)
    rmc.export()
    print("✅ Resonant Memory Cache stabilization complete.")