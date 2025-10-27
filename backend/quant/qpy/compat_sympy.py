# ================================================================
# 🔗 QPy SymPy Compatibility Layer (Full Integration)
# ================================================================
"""
Provides a unified interface to SymPy for the QPy symbolic stack.
Ensures all expected symbolic primitives (Symbol, Eq, integrate, etc.)
are safely exposed for MathKernel, LogicGlyph, and Codex modules.
"""

import sympy as _sym
from sympy import (
    sin, cos, diff, simplify, sympify, solve, symbols, expand, Eq,
    Matrix, latex, pretty, limit, nsimplify, Derivative, Integral,
    integrate, series, solveset, S, And, Or, Symbol
)

# ================================================================
# ✅ Direct passthroughs for symbolic operations
# ================================================================
qsin = sin
qcos = cos
qdiff = diff
qsimplify = simplify

# ================================================================
# 🧩 Safe fallbacks and undefined handler
# ================================================================
def qundef(*args, **kwargs):
    """Placeholder that returns None when an operation is undefined."""
    return None

def _noop(*a, **k):
    """Fallback for missing sympy functions (never used if SymPy available)."""
    return None

# ================================================================
# ✅ Export table — everything expected by MathKernel and LogicGlyph
# ================================================================
__all__ = [
    "sin", "cos", "diff", "simplify", "sympify", "solve", "symbols", "expand",
    "Eq", "Matrix", "latex", "pretty", "limit", "nsimplify", "Derivative",
    "Integral", "integrate", "series", "solveset", "S", "And", "Or", "Symbol",
    "qsin", "qcos", "qdiff", "qsimplify", "qundef"
]