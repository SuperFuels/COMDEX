# File: backend/modules/glyphos/symbolic_operator.py

"""
Symbolic operator utilities for CodexCore and SQI runtime.
Includes entanglement, superposition, and collapse detection.
"""

def is_entanglement_operator(glyph: str) -> bool:
    """
    Return True if the glyph represents an entanglement operator.
    Examples: ↔ (link), ⊗ (tensor entanglement), ≡ (equivalence entanglement)
    """
    return glyph in {"↔", "⊗", "≡"}


def is_superposition_operator(glyph: str) -> bool:
    """
    Return True if the glyph represents a superposition operator.
    Examples: ⊕ (superpose), ⧑ (entangled sum)
    """
    return glyph in {"⊕", "⧑"}


def is_collapse_operator(glyph: str) -> bool:
    """
    Return True if the glyph represents a collapse operator.
    Examples: ⧖ (collapse), ⊙ (observer collapse)
    """
    return glyph in {"⧖", "⊙"}


def is_quantum_operator(glyph: str) -> bool:
    """
    Return True if the glyph is any kind of symbolic quantum operator.
    """
    return any([
        is_entanglement_operator(glyph),
        is_superposition_operator(glyph),
        is_collapse_operator(glyph),
    ])