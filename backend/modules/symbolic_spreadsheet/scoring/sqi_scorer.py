# File: backend/modules/symbolic_spreadsheet/scoring/sqi_scorer.py

import math
from typing import TYPE_CHECKING, Dict, Any

# Lazy pattern scoring setup
detect_patterns = None
pattern_sqi_scorer = None

try:
    from backend.modules.patterns.symbolic_pattern_engine import SymbolicPatternEngine
    from backend.modules.patterns.pattern_sqi_scorer import pattern_sqi_scorer as _pattern_scorer_instance

    _pattern_engine = SymbolicPatternEngine()
    pattern_sqi_scorer = _pattern_scorer_instance

    def detect_patterns(logic: str):
        glyphs = [{"type": "symbol", "text": logic}]
        return _pattern_engine.detect_patterns(glyphs)

except ImportError as e:
    print(f"[SQI:Init] Pattern engine import failed: {e}")
    detect_patterns = None
    pattern_sqi_scorer = None

if TYPE_CHECKING:
    from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell


def score_sqi(cell: "GlyphCell") -> float:
    """
    📈 Compute the Symbolic Quality Index (SQI) score for a GlyphCell.

    Scoring Factors:
    - Base: 0.5
    - Trace bonus: +0.2 per trace entry
    - Emotion boost: +0.3 if emotion is "inspired"
    - Prediction bonus: +0.1 * word count of prediction
    - Logic complexity bonus: +0.05 * word count of logic
    - Pattern bonus: + PatternSQIScorer.score_pattern() if match is found
    - Mutation penalty/bonus via adjust_sqi_for_mutation()
    """
    if not isinstance(cell, object) or not hasattr(cell, "logic") or not hasattr(cell, "trace"):
        raise TypeError("Input must be a GlyphCell-like object")

    base = 0.5
    trace_bonus = 0.2 * len(cell.trace)
    emotion_bonus = 0.3 if getattr(cell, "emotion", "") == "inspired" else 0.0
    prediction_bonus = 0.1 * len(getattr(cell, "prediction", "").split())
    logic_bonus = 0.05 * len(getattr(cell, "logic", "").split())

    # Advanced Pattern SQI scoring
    pattern_bonus = 0.0
    if detect_patterns and callable(detect_patterns) and pattern_sqi_scorer:
        try:
            matches = detect_patterns(cell.logic)
            if isinstance(matches, list) and matches:
                top_match = matches[0]
                pattern_score = pattern_sqi_scorer.score_pattern(top_match)
                pattern_bonus = pattern_score.get("sqi_score", 0.0)
        except Exception as e:
            print(f"[SQI:Pattern] Pattern scoring failed: {e}")

    total_score = base + trace_bonus + emotion_bonus + prediction_bonus + logic_bonus + pattern_bonus

    # 🧬 Mutation-aware SQI scoring adjustment
    if hasattr(cell, "logic_tree") and isinstance(cell.logic_tree, dict):
        total_score = adjust_sqi_for_mutation(total_score, cell.logic_tree)

    return round(min(1.0, total_score), 4)


def adjust_sqi_for_mutation(base_sqi: float, logic_node: Dict[str, Any]) -> float:
    """
    Adjusts the SQI score based on whether the node has been mutated.
    Penalizes high mutation density or contradiction.
    Rewards thoughtful, pattern-aligned mutation when noted.
    """
    if not isinstance(logic_node, dict):
        return base_sqi

    penalty = 0.0
    boost = 0.0

    # Check for direct mutation
    if logic_node.get("mutated"):
        note = logic_node.get("mutation_note", "")
        if "contradiction" in note:
            penalty += 0.25
        elif "remove_leaf" in note:
            penalty += 0.15
        elif "rename" in note or "change" in note:
            penalty += 0.1
        elif "duplicate" in note or "swap" in note:
            boost += 0.1

    # Recurse through children
    for child in logic_node.get("children", []):
        if isinstance(child, dict):
            base_sqi = adjust_sqi_for_mutation(base_sqi, child)

    # Apply penalty/boost
    base_sqi = base_sqi - penalty + boost
    return max(0.0, min(base_sqi, 1.0))  # Clamp between 0 and 1