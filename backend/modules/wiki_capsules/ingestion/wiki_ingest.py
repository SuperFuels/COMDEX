#!/usr/bin/env python3
"""
WikiCapsule → AION Ingestion Bridge
────────────────────────────────────────────
Loads static .wiki.enriched.phn capsules and injects them
into AION’s symbolic memory and resonance fabric.

Usage:
    PYTHONPATH=. python backend/modules/wiki_capsules/ingestion/wiki_ingest.py \
        --dir data/knowledge/Lexicon_enriched \
        --commit --verbose
"""

import argparse
import logging
from pathlib import Path

# ───────────────────────────────
# Core Imports (Tessaris hierarchy)
# ───────────────────────────────
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import WikiCapsule

# KG integration fallback-safe import
try:
    from backend.modules.wiki_capsules.integration.kg_query_extensions import register_kg_entry
except ImportError:
    def register_kg_entry(title: str, content: str):
        logging.getLogger("WikiIngest→AION").warning(
            f"[Fallback] Missing kg_query_extensions — simulated KG entry for: {title}"
        )
        return {"title": title, "content_len": len(content)}

# AION imports (memory + resonance)
try:
    from backend.modules.aion.memory.store import store_capsule_metadata, commit_memory
    from backend.AION.resonance.resonance_engine import update_resonance
except ImportError:
    # Graceful degradation when AION modules are not mounted
    def store_capsule_metadata(title, meta):
        logging.getLogger("WikiIngest→AION").warning(f"[Fallback] store_capsule_metadata missing for {title}")

    def commit_memory():
        logging.getLogger("WikiIngest→AION").warning("[Fallback] commit_memory not available")

    def update_resonance(title, keywords=None):
        logging.getLogger("WikiIngest→AION").warning(f"[Fallback] update_resonance missing for {title}")


# ───────────────────────────────
# Logging Setup
# ───────────────────────────────
log = logging.getLogger("WikiIngest→AION")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")


# ───────────────────────────────
# Utility: Safe Keyword Extraction
# ───────────────────────────────
def _safe_str_list(items):
    """Flatten and stringify nested or dict-based synonym/antonym lists."""
    safe = []
    for x in items or []:
        if isinstance(x, dict):
            # Try to extract a representative value (e.g., {"word": "reduce"})
            v = x.get("word") or x.get("lemma") or next(iter(x.values()), None)
            if v:
                safe.append(str(v))
        elif isinstance(x, (list, tuple, set)):
            for i in x:
                safe.append(str(i))
        else:
            safe.append(str(x))
    return safe


# ───────────────────────────────
# Capsule Ingestion
# ───────────────────────────────
def ingest_static_capsule(path: Path) -> bool:
    """Load and ingest one .wiki.enriched.phn capsule into AION."""
    try:
        # Always parse via WikiCapsule.load to normalize legacy keys like 'title'
        capsule = WikiCapsule.load(path)

        title = getattr(capsule, "lemma", path.stem)
        content = "\n".join(capsule.definitions or [])

        # Extract keywords safely (avoid dict hashing)
        syns = _safe_str_list(getattr(capsule, "synonyms", []))
        ants = _safe_str_list(getattr(capsule, "antonyms", []))
        keywords = list(set(syns + ants))

        # Register in KG and Memory layers
        register_kg_entry(title, content)
        store_capsule_metadata(capsule, domain="Lexicon")

        # Trigger resonance recalibration
        update_resonance(title, keywords)

        log.info(f"✅ Ingested capsule: {title}")
        return True

    except Exception as e:
        log.error(f"⚠️ Failed to ingest {path}: {e}")
        return False


# ───────────────────────────────
# Directory Ingestion
# ───────────────────────────────
def ingest_directory(source_dir: Path, commit: bool = False, verbose: bool = False):
    """Ingest all .wiki.enriched.phn capsules in a directory."""
    files = sorted(source_dir.rglob("*.wiki.enriched.phn"))
    log.info(f"Found {len(files)} enriched capsules to ingest.")
    success = 0

    for f in files:
        ok = ingest_static_capsule(f)
        if ok:
            success += 1
        elif verbose:
            log.warning(f"[Skip] {f.name}")

    log.info(f"[AION-Ingest] Completed: {success}/{len(files)} capsules ingested.")

    if commit:
        try:
            commit_memory()
            log.info("💾 Commit: Resonance + Memory Store updated.")
        except Exception as e:
            log.warning(f"Commit skipped or failed: {e}")

    return success


# ───────────────────────────────
# CLI Entrypoint
# ───────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=str, required=True, help="Directory containing .wiki.enriched.phn capsules")
    parser.add_argument("--commit", action="store_true", help="Commit changes to AION persistent memory")
    parser.add_argument("--verbose", action="store_true", help="Verbose output for skipped capsules")
    args = parser.parse_args()

    ingest_directory(Path(args.dir), commit=args.commit, verbose=args.verbose)