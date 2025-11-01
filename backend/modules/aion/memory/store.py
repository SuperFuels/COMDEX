"""
AION Symbolic Memory Store - Phase 10
────────────────────────────────────────────
Persistent memory layer for capsule metadata and resonance snapshots.
Integrates with the Knowledge Graph and Resonance Engine.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Union

from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import WikiCapsule
from backend.modules.wiki_capsules.integration.kg_query_extensions import (
    add_capsule_to_kg,
    update_capsule_meta,
)
from backend.AION.resonance.resonance_engine import update_resonance

# ───────────────────────────────
# Paths and I/O
# ───────────────────────────────
STORE_PATH = Path("data/aion/memory_store.json")
STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

CapsuleLike = Union[WikiCapsule, Dict[str, Any]]


def _load() -> dict:
    """Load current symbolic memory snapshot."""
    if STORE_PATH.exists():
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(state: dict) -> None:
    """Persist symbolic memory state to disk."""
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# ───────────────────────────────
# Core Metadata Handling
# ───────────────────────────────
def _capsule_to_dict(c: CapsuleLike) -> Dict[str, Any]:
    if hasattr(c, "to_dict"):
        return c.to_dict()
    return dict(c)


def store_capsule_metadata(capsule: CapsuleLike, domain: str = "Lexicon") -> None:
    """
    Ensure capsule is registered in the KG and persist/merge its metadata.
    Also records its resonance snapshot (including energy E) into AION memory.
    """
    cdict = _capsule_to_dict(capsule)
    lemma = cdict.get("lemma")
    if not lemma:
        raise ValueError("Capsule must include a 'lemma' field")

    meta = cdict.get("meta", {}) or {}
    meta["timestamp"] = time.time()

    # Update Knowledge Graph metadata
    try:
        update_capsule_meta(lemma, domain, meta)
    except KeyError:
        add_capsule_to_kg(capsule, domain, capsule_path=None)
        update_capsule_meta(lemma, domain, meta)

    # 🔬 Pull latest resonance data (with energy E)
    resonance = update_resonance(lemma, cdict.get("synonyms", []))
    if resonance:
        meta.update({
            "SQI": resonance.get("SQI"),
            "ρ": resonance.get("ρ"),
            "Ī": resonance.get("Ī"),
            "E": resonance.get("E"),
        })

    # Persist merged state
    state = _load()
    state[lemma] = meta
    _save(state)

    print(f"[AION-Memory] Stored metadata for {lemma} (Lexicon) -> E={meta.get('E')}")


# ───────────────────────────────
# Commit Operation
# ───────────────────────────────
def commit_memory() -> None:
    """Flush current memory and mark a commit event."""
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    print(f"[AION-Memory] Commit complete ✅  ({stamp})")