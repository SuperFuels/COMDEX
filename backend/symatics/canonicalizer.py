# backend/symatics/canonicalizer.py
# ---------------------------------------------------------------------
# Canonicalizer for Symatics expressions
# - Converts arbitrary expression trees into canonical tuple form
# - Used by rewrite rules, law checks, and equivalence testing
# ---------------------------------------------------------------------
# [Tessaris v0.2] Canonicalization Mirror (Passive, Lazy Import)
# ---------------------------------------------------------------------
# This file is retained for backward compatibility with legacy COMDEX modules.
# It lazily delegates canonicalization to the authoritative implementation
# in backend.symatics.symatics_rulebook to avoid circular imports.
# ---------------------------------------------------------------------

from typing import Any

def _canonical(expr: Any) -> Any:
    """Lazy proxy to rulebook._canonical to avoid circular import at import time."""
    from backend.symatics.symatics_rulebook import _canonical as real_canonical
    return real_canonical(expr)

def canonical(expr: Any) -> Any:
    """Public alias for canonicalization (lazy delegated)."""
    from backend.symatics.symatics_rulebook import _canonical as real_canonical
    return real_canonical(expr)

__all__ = ["canonical", "_canonical"]