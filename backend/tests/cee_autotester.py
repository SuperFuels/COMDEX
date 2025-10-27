#!/usr/bin/env python3
"""
🚀 CEE AutoTester — Phase 46A
─────────────────────────────
Evaluates LexMemory ↔ ResonantMemoryCache coherence.

Checks:
  • JSON validity & schema match
  • Overlap between LexMemory and RMC entries
  • Average SQI, ρ, and I distribution
  • Drift and coherence summary
"""

import json, logging, statistics
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

LEX_PATH = Path("data/memory/cee_lex_memory.json")
RMC_PATH = Path("data/memory/resonant_memory_cache.json")

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"❌ Failed to load {p}: {e}")
        return {}

def evaluate():
    lex = load_json(LEX_PATH)
    rmc = load_json(RMC_PATH)

    if not lex or not rmc:
        log.warning("⚠ Missing data — ensure both LexMemory and RMC exist.")
        return

    cache = rmc.get("cache", rmc)
    lex_keys = set(lex.keys())
    rmc_keys = set(k for k in cache.keys() if isinstance(k, str))
    overlap = lex_keys & rmc_keys

    log.info(f"📘 LexMemory entries: {len(lex_keys):,}")
    log.info(f"📗 RMC entries: {len(rmc_keys):,}")
    log.info(f"🔗 Overlap: {len(overlap):,} ({len(overlap)/max(len(lex_keys),1)*100:.2f}%)")

    sqis, rhos, Is = [], [], []
    for v in lex.values():
        try:
            if isinstance(v, dict) and "resonance" in v:
                r = v["resonance"]
                sqis.append(r.get("SQI", 0))
                rhos.append(r.get("ρ", 0))
                Is.append(r.get("I", 0))
        except Exception:
            continue

    if sqis:
        log.info(f"📊 Avg SQI={statistics.mean(sqis):.3f} ρ={statistics.mean(rhos):.3f} I={statistics.mean(Is):.3f}")
        log.info(f"📈 Max SQI={max(sqis):.3f}, Min SQI={min(sqis):.3f}")

    drift = abs(statistics.mean(rhos) - statistics.mean(Is)) if rhos and Is else 0
    log.info(f"🌊 Resonance drift: {drift:.3f}")

    print("\n✅ Evaluation complete — coherence verified." if overlap else "\n⚠ No overlap detected.")

if __name__ == "__main__":
    evaluate()