# ================================================================
# ⚙️ CEE LexMemory Maintenance — Resonance Drift Correction
# Phase 46A — Entropy Cleanup & SQI Normalization
# ================================================================
"""
Performs background maintenance on the LexMemory store.
Tasks:
  • Decay old resonance fields over time
  • Normalize SQI distributions
  • Prune weak/noisy associations
  • Keep the resonance field coherent across sessions
"""

import time, math, logging
from .cee_lex_memory import _load_memory, _save_memory, decay_memory

logger = logging.getLogger(__name__)

def rebalance_memory(norm_target: float = 0.5, floor: float = 0.05, min_count: int = 1):
    mem = _load_memory()
    changed = 0
    for k, v in mem.items():
        if v.get("count", 0) >= min_count:
            sqi = v.get("SQI", 0.0)
            new_sqi = max(floor, (sqi + norm_target) / 2)
            if abs(new_sqi - sqi) > 1e-3:
                v["SQI"] = round(new_sqi, 3)
                changed += 1
    _save_memory(mem)
    logger.info(f"[LexMemoryMaint] Rebalanced {changed} entries toward SQI≈{norm_target}")

def prune_weak(threshold: float = 0.12, min_count: int = 0):
    mem = _load_memory()
    kept = {k: v for k, v in mem.items()
            if v.get("SQI", 0) >= threshold or v.get("count", 0) > min_count}
    removed = len(mem) - len(kept)
    if removed:
        _save_memory(kept)
    logger.info(f"[LexMemoryMaint] Pruned {removed} weak/noisy associations")

def maintenance_job(half_life_hours: float = 72.0):
    start = time.time()
    decay_memory(half_life_hours)
    rebalance_memory()
    prune_weak()
    logger.info(f"[LexMemoryMaint] Completed maintenance in {round(time.time()-start,2)}s")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    maintenance_job()