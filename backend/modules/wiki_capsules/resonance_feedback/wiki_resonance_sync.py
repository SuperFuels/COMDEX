"""
wiki_resonance_sync.py
──────────────────────────────────────────────
Bridges resonance feedback between Aion’s runtime and Wiki Capsules.
Synchronizes updated SQI metrics back into static capsule metadata.
"""

from typing import Dict
from .resonance_alignment import align_resonance, ResonanceState

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
    for k in ("ρ", "Ī", "sqi_score"):
        if k in aion_feedback:
            merged[k] = (merged.get(k, 0) + aion_feedback[k]) / 2

    new_state = align_resonance(merged)
    wiki_meta.update({
        "ρ": new_state.rho,
        "Ī": new_state.Ibar,
        "sqi_score": new_state.sqi_score
    })
    return new_state