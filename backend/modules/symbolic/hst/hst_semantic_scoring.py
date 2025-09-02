from typing import List, Union
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import SymbolGlyph
from backend.modules.symbolnet.symbolnet_loader import get_semantic_vector, cosine_similarity

def semantic_distance(g1: Union[SymbolGlyph, str], g2: Union[SymbolGlyph, str]) -> float:
    """
    Returns the cosine distance (1 - similarity) between two glyphs or labels based on semantic vectors.
    """
    label1 = g1.label if isinstance(g1, SymbolGlyph) else str(g1)
    label2 = g2.label if isinstance(g2, SymbolGlyph) else str(g2)

    v1 = get_semantic_vector(label1)
    v2 = get_semantic_vector(label2)

    if v1 is None or v2 is None:
        return 1.0  # Maximum distance if missing

    similarity = cosine_similarity(v1, v2)
    return 1.0 - similarity


def concept_match(glyph: Union[SymbolGlyph, str], concept_vec: List[float]) -> float:
    """
    Returns similarity between a glyph or label and a given concept vector.
    """
    label = glyph.label if isinstance(glyph, SymbolGlyph) else str(glyph)
    gv = get_semantic_vector(label)

    if gv is None:
        return 0.0
    return cosine_similarity(gv, concept_vec)