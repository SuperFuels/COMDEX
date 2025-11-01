"""
Wiki ↔ AION Resonance Sync
────────────────────────────────────────────
Bridges resonance feedback between Aion's runtime and Wiki Capsules.
Synchronizes updated SQI / ρ / Ī metrics back into static capsule metadata.
"""

from typing import Dict
from pathlib import Path
import json

from backend.AION.resonance.resonance_engine import get_resonance
from backend.modules.wiki_capsules.integration.kg_query_extensions import (
    _load_registry,
    _save_registry,
)
from .resonance_alignment import align_resonance, ResonanceState


# ───────────────────────────────────────────────
# Capsule-Level Merge
# ───────────────────────────────────────────────
def sync_wiki_resonance(wiki_meta: Dict[str, float],
                        aion_feedback: Dict[str, float]) -> ResonanceState:
    """
    Merge Aion feedback metrics into Wiki Capsule meta block.

    Args:
        wiki_meta: current capsule metadata (ρ, Ī, sqi_score)
        aion_feedback: resonance metrics returned by Aion engine

    Returns:
        ResonanceState representing the new unified resonance state.
    """
    merged = dict(wiki_meta)
    for k in ("ρ", "Ī", "sqi_score", "SQI"):
        if k in aion_feedback:
            merged[k] = (merged.get(k, 0.0) + float(aion_feedback[k])) / 2.0

    # Align through resonance model
    new_state = align_resonance(merged)
    wiki_meta.update({
        "ρ": new_state.rho,
        "Ī": new_state.Ibar,
        "sqi_score": new_state.sqi_score,
    })
    return new_state


# ───────────────────────────────────────────────
# Global KG Synchronization
# ───────────────────────────────────────────────
def sync_resonance_with_kg(domain: str = "Lexicon"):
    """
    Synchronize all registered Wiki Capsules in a given domain
    with their corresponding AION resonance states.
    """
    reg = _load_registry()
    dom = reg.get(domain, {})
    if not dom:
        print(f"[Resonance-Sync] No KG entries found in {domain}")
        return

    updated = 0
    for lemma, entry in dom.items():
        res_state = get_resonance(lemma)
        if not res_state:
            continue

        meta = entry.get("meta", {}) or {}
        meta.update({
            "SQI": res_state.get("SQI"),
            "ρ": res_state.get("ρ"),
            "Ī": res_state.get("Ī"),
        })
        entry["meta"] = meta
        updated += 1

    _save_registry(reg)
    print(f"[Resonance-Sync] Updated {updated} entries in {domain}")