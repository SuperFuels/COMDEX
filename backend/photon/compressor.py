# backend/photon/compressor.py
"""
Photon Compressor
-----------------
Two-tier Photon compression engine:

Basic mode:
  - Dedup identical subtrees (structural sharing).
  - Flatten nested ⊕ (Add) and ⊗ (Mul).

Advanced mode:
  - Lazy gradient compaction (keep Grad nodes unexpanded).
  - Subtree factoring: collapse repeats (x ⊕ y ⊕ x → 2*(x ⊕ y)).
  - Aggressive ⊕ / ⊗ flattening with hash-sharing.
"""

import sympy as sp
from sympy.core.function import AppliedUndef
from backend.photon.rewriter import Grad, _glyph_to_sympy


class PhotonCompressor:
    def __init__(self):
        self.cache = {}

    # ------------------------
    # Core helpers
    # ------------------------
    def _hash_tree(self, expr):
        """Hash a SymPy expression structurally."""
        return sp.srepr(expr)

    def _dedup(self, expr):
        """Replace repeated subtrees with single instances (structural sharing)."""
        h = self._hash_tree(expr)
        if h in self.cache:
            return self.cache[h]
        if expr.args:
            new_args = tuple(self._dedup(a) for a in expr.args)
            if new_args != expr.args:
                expr = expr.func(*new_args)
        self.cache[h] = expr
        return expr

    def _flatten_ops(self, expr):
        """Flatten nested ⊕ and ⊗ (Add/Mul)."""
        if isinstance(expr, sp.Add):
            terms = []
            for a in expr.args:
                if isinstance(a, sp.Add):
                    terms.extend(a.args)
                else:
                    terms.append(a)
            return sp.Add(*terms)
        if isinstance(expr, sp.Mul):
            factors = []
            for a in expr.args:
                if isinstance(a, sp.Mul):
                    factors.extend(a.args)
                else:
                    factors.append(a)
            return sp.Mul(*factors)
        return expr

    def _factor_repeats(self, expr):
        """Factor repeated terms in sums/products."""
        if isinstance(expr, sp.Add):
            counts = {}
            for t in expr.args:
                counts[t] = counts.get(t, 0) + 1
            new_terms = []
            for t, c in counts.items():
                if c == 1:
                    new_terms.append(t)
                else:
                    new_terms.append(c * t)
            return sp.Add(*new_terms)
        if isinstance(expr, sp.Mul):
            counts = {}
            for t in expr.args:
                counts[t] = counts.get(t, 0) + 1
            new_factors = []
            for t, c in counts.items():
                if c == 1:
                    new_factors.append(t)
                else:
                    new_factors.append(t**c)
            return sp.Mul(*new_factors)
        return expr

    # ------------------------
    # Compression passes
    # ------------------------
    def compress_basic(self, expr: str):
        """Basic compression: dedup + flatten."""
        expr_std = _glyph_to_sympy(expr)
        expr_sym = sp.sympify(expr_std, locals={"Grad": Grad})

        expr_sym = self._dedup(expr_sym)
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)), self._flatten_ops
        )

        return expr_sym

    def compress_advanced(self, expr: str):
        """Advanced compression: lazy ∇ + factoring + flattening."""
        expr_std = _glyph_to_sympy(expr)
        expr_sym = sp.sympify(expr_std, locals={"Grad": Grad})

        # Lazy gradient (leave Grad unexpanded)
        # Deduplication
        expr_sym = self._dedup(expr_sym)

        # Flatten ⊕ / ⊗
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)), self._flatten_ops
        )

        # Factor repeats
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)), self._factor_repeats
        )

        return expr_sym

    # ------------------------
    # Entry points
    # ------------------------
    def normalize_compressed(self, expr: str, mode="basic"):
        """
        Normalize with compression.
        mode = "basic" (default) or "advanced"
        """
        self.cache.clear()
        if mode == "basic":
            return self.compress_basic(expr)
        elif mode == "advanced":
            return self.compress_advanced(expr)
        else:
            raise ValueError(f"Unknown mode: {mode}")


# Singletons for convenience
compressor = PhotonCompressor()
compressor_basic = compressor.compress_basic
compressor_adv = compressor.compress_advanced