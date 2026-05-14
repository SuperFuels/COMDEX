# backend/modules/sqi/sqi_engine.py

"""
Thin wrapper so older/importing modules can call evaluate_sqi()
using new SQI engine internals in sqi_scorer.py
"""

from typing import List, Dict, Any
from backend.modules.sqi.sqi_scorer import (
    score_all_electrons,
    score_pattern_sqi,
    inject_sqi_scores_into_container
)


def evaluate_sqi(glyphs: List[Dict[str, Any]]) -> float:
    """
    Accepts raw glyph list and returns average SQI.
    Compatible shim for atom_save + CodexLang pipeline.
    """
    if not glyphs:
        return 0.0
    
    result = score_all_electrons(glyphs)
    if not result:
        return 0.0

    scores = [v["score"] for v in result.values() if isinstance(v, dict)]
    if not scores:
        return 0.0

    return round(sum(scores) / len(scores), 4)


# Utility export for pattern scoring
def evaluate_pattern_sqi(pattern: Dict[str, Any]) -> float:
    return score_pattern_sqi(pattern)


__all__ = [
    "evaluate_sqi",
    "evaluate_pattern_sqi",
    "inject_sqi_scores_into_container"
]