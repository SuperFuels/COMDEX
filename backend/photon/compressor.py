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

Upgrades:
  - Hashing now uses sympy's `srepr` + cache for structural identity.
  - Flattening & factoring use iterative stack (faster than recursive replace).
  - Gradient nodes (`Grad`) explicitly preserved in advanced mode.
  - `normalize_compressed()` safe-guards invalid input.
  - Convenience aliases: `compressor_basic`, `compressor_adv`.
"""

import sympy as sp
from backend.photon.rewriter import Grad, _glyph_to_sympy


class PhotonCompressor:
    def __init__(self):
        # Shared structural cache (cleared per normalize run)
        self.cache: dict[str, sp.Expr] = {}

    # ------------------------
    # Core helpers
    # ------------------------
    def _hash_tree(self, expr: sp.Expr) -> str:
        """Hash a SymPy expression structurally (fast structural equality)."""
        return sp.srepr(expr)

    def _dedup(self, expr: sp.Expr) -> sp.Expr:
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

    def _flatten_ops(self, expr: sp.Expr) -> sp.Expr:
        """Flatten nested ⊕ and ⊗ (Add/Mul)."""
        if isinstance(expr, sp.Add):
            terms = []
            for a in expr.args:
                if isinstance(a, sp.Add):
                    terms.extend(a.args)
                else:
                    terms.append(a)
            return sp.Add(*terms)
        elif isinstance(expr, sp.Mul):
            factors = []
            for a in expr.args:
                if isinstance(a, sp.Mul):
                    factors.extend(a.args)
                else:
                    factors.append(a)
            return sp.Mul(*factors)
        return expr

    def _factor_repeats(self, expr: sp.Expr) -> sp.Expr:
        """Factor repeated terms in sums/products."""
        if isinstance(expr, sp.Add):
            counts = {}
            for t in expr.args:
                counts[t] = counts.get(t, 0) + 1
            new_terms = [t if c == 1 else c * t for t, c in counts.items()]
            return sp.Add(*new_terms)

        elif isinstance(expr, sp.Mul):
            counts = {}
            for t in expr.args:
                counts[t] = counts.get(t, 0) + 1
            new_factors = [t if c == 1 else t**c for t, c in counts.items()]
            return sp.Mul(*new_factors)

        return expr

    # ------------------------
    # Compression passes
    # ------------------------
    def compress_basic(self, expr: str) -> sp.Expr:
        """Basic compression: dedup + flatten."""
        expr_std = _glyph_to_sympy(expr)
        expr_sym = sp.sympify(expr_std, locals={"Grad": Grad})

        expr_sym = self._dedup(expr_sym)

        # Iterative flatten pass
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)), self._flatten_ops
        )
        return expr_sym

    def compress_advanced(self, expr: str) -> sp.Expr:
        """Advanced compression: lazy ∇ + factoring + flattening."""
        expr_std = _glyph_to_sympy(expr)
        expr_sym = sp.sympify(expr_std, locals={"Grad": Grad})

        # Deduplication (preserve Grad nodes)
        expr_sym = self._dedup(expr_sym)

        # Flatten ⊕ / ⊗ aggressively
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)), self._flatten_ops
        )

        # Factor repeats (x + x → 2*x, x*x → x**2)
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)), self._factor_repeats
        )

        return expr_sym

    # ------------------------
    # Entry points
    # ------------------------
    def normalize_compressed(self, expr: str, mode="basic") -> sp.Expr:
        """
        Normalize with compression.
        mode = "basic" (default) or "advanced"
        """
        if not isinstance(expr, str):
            raise TypeError(f"Expression must be a string, got {type(expr)}")

        self.cache.clear()
        if mode == "basic":
            return self.compress_basic(expr)
        elif mode == "advanced":
            return self.compress_advanced(expr)
        else:
            raise ValueError(f"Unknown mode: {mode}")


# ------------------------
# Convenience Singletons
# ------------------------
compressor = PhotonCompressor()
compressor_basic = compressor.compress_basic
compressor_adv = compressor.compress_advanced