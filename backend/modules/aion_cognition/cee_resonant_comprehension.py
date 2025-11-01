#!/usr/bin/env python3
# ================================================================
# 🧠 AION Resonant Comprehension - Phase 18 (Concept Linkage Layer)
# ================================================================
"""
This module extends AION's cognitive framework beyond lexical recall,
introducing phase-level comprehension and contextual resonance.

Functions:
  * train_phrase_associations() - build concept-pair resonance from lemmas
  * measure_context_resonance() - compute SQI for multi-word contexts
  * reinforce_emotive_field() - encode affective tone and contextual emotion

Dependencies:
  - cee_lex_memory (for lemma recall)
  - resonant_memory_cache (for resonance aggregation)
  - conversation_memory (for context continuity)
"""

import math, random, logging, time
from typing import Dict, List, Tuple

from backend.modules.aion_cognition.cee_lex_memory import recall_from_memory, reinforce_field
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_language.conversation_memory import MEM

log = logging.getLogger(__name__)
RMC = ResonantMemoryCache()

# ================================================================
def _resonance_pair(a: Dict, b: Dict) -> float:
    """Compute contextual resonance (SQI) between two lemma memory entries."""
    try:
        ρa, Ia = a.get("resonance", {}).get("ρ", 0.5), a.get("resonance", {}).get("I", 0.5)
        ρb, Ib = b.get("resonance", {}).get("ρ", 0.5), b.get("resonance", {}).get("I", 0.5)
        sqi = round(((ρa + ρb) / 2 + (Ia + Ib) / 2) / 2, 3)
        return sqi
    except Exception:
        return 0.0

# ================================================================
def train_phrase_associations(phrases: List[str]) -> List[Dict]:
    """
    Build resonance links between adjacent lemmas within phrases.
    Example input: ["light wave", "quantum field", "energy resonance"]
    """
    associations = []
    for phrase in phrases:
        tokens = phrase.lower().split()
        for i in range(len(tokens) - 1):
            a, b = tokens[i], tokens[i + 1]
            A = recall_from_memory(a) or {}
            B = recall_from_memory(b) or {}
            sqi = _resonance_pair(A, B)
            RMC.update_resonance_link(a, b, sqi)
            associations.append({"a": a, "b": b, "SQI": sqi})
            log.info(f"[ResonantComprehension] Linked {a}↔{b} with SQI={sqi}")
    return associations

# ================================================================
def measure_context_resonance(context: str) -> float:
    """
    Compute average contextual SQI for a given sentence or phrase.
    This measures how semantically coherent the phrase is within AION's field.
    """
    tokens = context.lower().split()
    if len(tokens) < 2:
        return 0.0

    total_sqi, count = 0.0, 0
    for i in range(len(tokens) - 1):
        A = recall_from_memory(tokens[i]) or {}
        B = recall_from_memory(tokens[i + 1]) or {}
        sqi = _resonance_pair(A, B)
        total_sqi += sqi
        count += 1

    avg_sqi = round(total_sqi / max(count, 1), 3)
    log.info(f"[ContextResonance] Context='{context}' -> SQI={avg_sqi}")
    return avg_sqi

# ================================================================
def reinforce_emotive_field(context: str, tone: str = "neutral"):
    """
    Store affective alignment in MEM, marking emotional resonance
    across learned conceptual fields (joy, calm, tension, focus).
    """
    sqi = measure_context_resonance(context)
    affect = {
        "neutral": 0.5, "joy": 0.9, "calm": 0.8, "tension": 0.4, "focus": 0.7
    }.get(tone, 0.5)
    combined = round((sqi + affect) / 2, 3)
    MEM.remember(context, f"{tone} field resonance SQI={combined}",
                 semantic_field="emotive_context")
    log.info(f"[EmotiveField] Reinforced tone={tone} with SQI={combined}")
    return combined

# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_phrases = ["light wave", "energy field", "quantum resonance"]
    train_phrase_associations(sample_phrases)
    measure_context_resonance("light interacts with wave")
    reinforce_emotive_field("light interacts with wave", tone="focus")