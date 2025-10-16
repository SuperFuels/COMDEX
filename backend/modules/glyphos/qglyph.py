# File: backend/modules/glyphos/qglyph.py
"""
QGlyph Core Utilities
=====================
Provides fundamental symbolic–quantum glyph operations:
  • resolve_qglyph_superposition — collapse superposed glyphs (↔)
  • normalize_glyph — optional utility to clean or canonicalize glyphs
"""

import random

def resolve_qglyph_superposition(left: str, right: str, bias: float = 0.5) -> str:
    """
    Resolves two superposed QGlyph states based on an observer bias value.

    Args:
        left:  String representing the left glyph (e.g. "[⚛:0]")
        right: String representing the right glyph (e.g. "[⚛:1]")
        bias:  Float in [0,1]; >0.5 favors left, <0.5 favors right.

    Returns:
        The collapsed glyph string.
    """
    if not isinstance(left, str) or not isinstance(right, str):
        raise TypeError("resolve_qglyph_superposition expects string glyphs")

    # Edge cases first
    if bias >= 1.0:
        return left
    if bias <= 0.0:
        return right

    # Probabilistic resolution
    roll = random.random()
    return left if roll < bias else right


def normalize_glyph(glyph: str) -> str:
    """Optional cleanup to ensure bracketed form like [⚛:x]."""
    if not glyph:
        return "[∅]"
    if not glyph.startswith("["):
        glyph = f"[{glyph}]"
    if not glyph.endswith("]"):
        glyph = glyph + "]"
    return glyph

# ────────────────────────────────────────────────────────────────
# 🧩 QGlyph Logic Preloader
# ────────────────────────────────────────────────────────────────

def preload_qglyph_logic(verbose: bool = True) -> dict:
    """
    Preloads QGlyph resonance tables, normalization rules, and quantum operator stubs
    used by Codex and QQC runtime.

    This function is called at Codex boot to ensure QGlyph-related symbolic mappings
    (⊕, ↔, ⟲, etc.) are registered and ready for quantum-glyph resolution.

    Returns:
        A dictionary of registered symbolic/quantum operators for reference.
    """

    qglyph_registry = {
        "superposition_resolver": resolve_qglyph_superposition,
        "normalize": normalize_glyph,
        "operators": {
            "⊕": "superpose",
            "↔": "entangle",
            "⟲": "resonate",
            "∇": "collapse",
            "μ": "measure",
        },
        "initialized": True,
    }

    if verbose:
        print("⚛️  QGlyph logic preloaded — symbolic quantum primitives available:")
        for sym, name in qglyph_registry["operators"].items():
            print(f"   • {sym}  → {name}")

    return qglyph_registry