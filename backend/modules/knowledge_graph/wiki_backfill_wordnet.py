#!/usr/bin/env python3
# ================================================================
# 🧠 AION Lexicon Backfill - Phase 17b (WordNet + LLM + Merge)
# ================================================================
"""
Fills remaining unenriched lexical capsules using WordNet and, if absent,
LLM-based fallback generation.  Produces a unified corpus ready for
AION's full lexical-conceptual training.

Inputs:
    /tmp/Lexicon_enriched           (≈41 k existing)
    data/knowledge/Lexicon          (≈102 k raw)
Outputs:
    /tmp/Lexicon_backfill
    /tmp/Lexicon_enriched_full      (merged 102 k set)
"""

import os, json, time, logging, shutil
from pathlib import Path
from tqdm import tqdm

# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------
log = logging.getLogger("backfill")
logging.basicConfig(level=logging.INFO, format="%(message)s")

LEXICON_SRC = Path("data/knowledge/Lexicon")
ENRICHED_DIR = Path("/tmp/Lexicon_enriched")
BACKFILL_DIR = Path("/tmp/Lexicon_backfill")
MERGED_DIR = Path("/tmp/Lexicon_enriched_full")

BACKFILL_DIR.mkdir(parents=True, exist_ok=True)
MERGED_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# WordNet loader
# ------------------------------------------------------------
try:
    from nltk.corpus import wordnet as wn
except Exception:
    import nltk
    nltk.download("wordnet")
    from nltk.corpus import wordnet as wn

# ------------------------------------------------------------
# Optional LLM fallback
# ------------------------------------------------------------
try:
    from backend.modules.aion_cognition.cee_llm_exercise_generator import generate_llm_exercise_batch
except Exception:
    generate_llm_exercise_batch = None
    log.warning("[Backfill] LLM generator not available - WordNet-only mode.")

# ------------------------------------------------------------
def wordnet_enrich(lemma: str):
    """Return simple dict with definition/example from WordNet."""
    synsets = wn.synsets(lemma)
    if not synsets:
        return None
    s = synsets[0]
    return {
        "definitions": [s.definition()],
        "examples": s.examples(),
        "source": "wordnet",
        "timestamp": time.time(),
    }

def llm_fallback(lemma: str):
    """Call LLM generator if available."""
    if not generate_llm_exercise_batch:
        return None
    items = generate_llm_exercise_batch(topic=lemma, count=1, test_type="definition")
    if not items:
        return None
    text = items[0].get("prompt") or items[0].get("answer")
    return {
        "definitions": [text],
        "examples": [],
        "source": "llm_fallback",
        "timestamp": time.time(),
    }

# ------------------------------------------------------------
def render_capsule(lemma: str, entry: dict):
    """Render minimal .wiki.enriched.phn capsule."""
    body = {
        "lemma": lemma,
        "source": entry.get("source"),
        "definitions": entry.get("definitions", []),
        "examples": entry.get("examples", []),
        "timestamp": entry.get("timestamp", time.time()),
        "meta": {"origin": entry.get("source"), "phase": "17b"},
    }
    return json.dumps(body, indent=2, ensure_ascii=False)

# ------------------------------------------------------------
def merge_all():
    """Merge enriched + backfill -> merged full."""
    log.info("🔄 Merging all enriched and backfill capsules...")
    for src_dir in (ENRICHED_DIR, BACKFILL_DIR):
        for file in src_dir.rglob("*.phn"):
            dst = MERGED_DIR / file.name
            shutil.copy2(file, dst)
    total = sum(1 for _ in MERGED_DIR.rglob("*.phn"))
    log.info(f"✅ Merge complete - total {total:,} capsules in {MERGED_DIR}")
    return total

# ------------------------------------------------------------
def main():
    enriched = {p.stem for p in ENRICHED_DIR.rglob("*.phn")}
    all_caps = [p for p in LEXICON_SRC.rglob("*.phn")]
    missing = [p for p in all_caps if p.stem not in enriched]

    log.info(f"🧩 Found {len(enriched):,} enriched | {len(missing):,} missing - starting backfill...")

    counters = {"wordnet": 0, "llm": 0, "skipped": 0}
    for path in tqdm(missing, total=len(missing)):
        lemma = path.stem
        entry = wordnet_enrich(lemma)
        if not entry:
            entry = llm_fallback(lemma)
        if not entry:
            counters["skipped"] += 1
            continue

        capsule = render_capsule(lemma, entry)
        out_path = BACKFILL_DIR / f"{lemma}.wiki.enriched.phn"
        out_path.write_text(capsule, encoding="utf-8")

        counters[entry["source"]] = counters.get(entry["source"], 0) + 1

    total_new = sum(v for v in counters.values())
    log.info(f"🏁 Backfill complete - new={total_new:,} (WordNet={counters.get('wordnet',0):,}, LLM={counters.get('llm_fallback',0):,}, skipped={counters['skipped']:,})")

    merge_all()
    log.info("🎯 Phase 17b complete - unified corpus ready for AION training.")

# ------------------------------------------------------------
if __name__ == "__main__":
    main()