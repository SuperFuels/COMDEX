# -*- coding: utf-8 -*-
"""
Photon Compressor — Tessaris / CFE v0.3.x
-----------------------------------------
Two-tier Photon compression engine:

Basic mode:
  • Dedup identical subtrees (structural sharing)
  • Flatten nested ⊕ (Add) and ⊗ (Mul)

Advanced mode:
  • Lazy gradient compaction (preserves Grad nodes)
  • Subtree factoring (x ⊕ y ⊕ x → 2*(x ⊕ y))
  • Aggressive flattening with structural cache reuse

Upgrades:
  • Safe bypass for dict/string/non-symbolic payloads
  • Hashing uses SymPy’s srepr() for structural identity
  • Iterative flatten/factor with caching (no recursion)
  • normalize_compressed() guards invalid input
  • Convenience aliases: compressor_basic, compressor_adv
"""

import sympy as sp
import logging
from backend.photon.rewriter import Grad, _glyph_to_sympy

logger = logging.getLogger(__name__)


class PhotonCompressor:
    def __init__(self):
        # Structural deduplication cache
        self.cache: dict[str, sp.Expr] = {}

    # =====================================================
    # Core helpers
    # =====================================================
    def _hash_tree(self, expr: sp.Expr) -> str:
        """Hash a SymPy expression structurally (fast equality)."""
        return sp.srepr(expr)

    def _dedup(self, expr: sp.Expr) -> sp.Expr:
        """Replace repeated subtrees with single shared instances."""
        h = self._hash_tree(expr)
        if h in self.cache:
            return self.cache[h]

        if hasattr(expr, "args") and expr.args:
            new_args = tuple(self._dedup(a) for a in expr.args)
            if new_args != expr.args:
                expr = expr.func(*new_args)

        self.cache[h] = expr
        return expr

    def _flatten_ops(self, expr: sp.Expr) -> sp.Expr:
        """Flatten nested ⊕ (Add) or ⊗ (Mul)."""
        if isinstance(expr, sp.Add):
            terms = []
            for a in expr.args:
                terms.extend(a.args if isinstance(a, sp.Add) else [a])
            return sp.Add(*terms)
        elif isinstance(expr, sp.Mul):
            factors = []
            for a in expr.args:
                factors.extend(a.args if isinstance(a, sp.Mul) else [a])
            return sp.Mul(*factors)
        return expr

    def _factor_repeats(self, expr: sp.Expr) -> sp.Expr:
        """Factor repeated terms in additive or multiplicative expressions."""
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

    # =====================================================
    # Compression passes
    # =====================================================
    def compress_basic(self, expr_sym) -> sp.Expr:
        """
        Basic compression:
        • Deduplication
        • Flatten ⊕ / ⊗
        Includes safe bypass for non-symbolic payloads.
        """
        # --- SAFETY BYPASS FOR RAW DATA PAYLOADS ---
        if not hasattr(expr_sym, "args"):
            logger.warning(f"[Compressor] Bypass triggered for non-symbolic payload ({type(expr_sym).__name__})")
            return expr_sym
        # -------------------------------------------

        expr_sym = self._dedup(expr_sym)
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)),
            self._flatten_ops,
        )
        return expr_sym

    def compress_advanced(self, expr_sym) -> sp.Expr:
        """
        Advanced compression:
        • Dedup + flatten + repeat factoring
        • Preserves Grad nodes and symbolic form
        """
        if not hasattr(expr_sym, "args"):
            logger.warning(f"[Compressor] Advanced bypass triggered for {type(expr_sym).__name__}")
            return expr_sym

        expr_sym = self._dedup(expr_sym)
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)),
            self._flatten_ops,
        )
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)),
            self._factor_repeats,
        )
        return expr_sym

    # =====================================================
    # Entry points
    # =====================================================
    def normalize_compressed(self, expr: str | sp.Expr, mode="basic") -> sp.Expr:
        """
        Normalize an expression string or SymPy tree using compression.
        mode = "basic" (default) or "advanced"
        """
        # Convert strings to symbolic form safely
        if isinstance(expr, str):
            expr = _glyph_to_sympy(expr)
            expr = sp.sympify(expr, locals={"Grad": Grad})

        self.cache.clear()
        if mode == "basic":
            return self.compress_basic(expr)
        elif mode == "advanced":
            return self.compress_advanced(expr)
        else:
            raise ValueError(f"Unknown compression mode: {mode}")


# =====================================================
# Convenience Singletons
# =====================================================
compressor = PhotonCompressor()
compressor_basic = compressor.compress_basic
compressor_adv = compressor.compress_advanced