import math
from typing import Optional, Dict, Any, List

from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import SymbolGlyph
from backend.modules.symbolnet.symbolnet_bridge import get_semantic_vector

# Placeholder: semantic vector type
Vector = List[float]

def cosine_similarity(v1: Vector, v2: Vector) -> float:
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def semantic_distance(glyph: SymbolGlyph, target_concept: str) -> float:
    """Lower = better semantic match"""
    glyph_vec = get_semantic_vector(glyph.label)
    goal_vec = get_semantic_vector(target_concept)
    similarity = cosine_similarity(glyph_vec, goal_vec)
    return 1.0 - similarity  # Lower is better

def goal_match_score(glyph: SymbolGlyph, goal: Optional[str]) -> float:
    if not goal:
        return 0.5
    distance = semantic_distance(glyph, goal)
    return max(0.0, 1.0 - distance)