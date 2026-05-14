# -*- coding: utf-8 -*-
"""
Photon Compressor - Tessaris / CFE v0.3.x
-----------------------------------------
Two-tier Photon compression engine.

Basic mode:
  * Dedup identical subtrees (structural sharing)
  * Flatten nested ⊕ (Add) and ⊗ (Mul)

Advanced mode:
  * Lazy gradient compaction (preserves Grad nodes)
  * Subtree factoring (x ⊕ y ⊕ x -> 2*x ⊕ y)
  * Aggressive flattening with structural cache reuse

Safety:
  * Bypass for dict/string/non-symbolic payloads
  * Hashing uses SymPy's srepr() for structural identity
  * normalize_compressed() guards invalid input
  * Convenience aliases: compressor_basic, compressor_adv

NOTE (LOCKED):
- ∇ is RESERVED for math gradient. This module preserves Grad(...) nodes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Union

import sympy as sp

# Reuse the canonical glyph→SymPy translator + Grad symbol from PhotonRewriter
from backend.photon.rewriter import Grad, _glyph_to_sympy

logger = logging.getLogger(__name__)


class PhotonCompressor:
    def __init__(self) -> None:
        # Structural deduplication cache (keyed by srepr)
        self.cache: Dict[str, sp.Expr] = {}

    # =====================================================
    # Core helpers
    # =====================================================
    def _hash_tree(self, expr: sp.Expr) -> str:
        """Hash a SymPy expression structurally (fast equality)."""
        return sp.srepr(expr)

    def _dedup(self, expr: sp.Expr) -> sp.Expr:
        """Replace repeated subtrees with single shared instances."""
        h = self._hash_tree(expr)
        hit = self.cache.get(h)
        if hit is not None:
            return hit

        if hasattr(expr, "args") and expr.args:
            new_args = tuple(self._dedup(a) for a in expr.args)
            if new_args != expr.args:
                expr = expr.func(*new_args)

        self.cache[h] = expr
        return expr

    def _flatten_ops(self, expr: sp.Expr) -> sp.Expr:
        """Flatten nested Add or Mul."""
        if isinstance(expr, sp.Add):
            terms = []
            for a in expr.args:
                terms.extend(a.args if isinstance(a, sp.Add) else [a])
            return sp.Add(*terms)
        if isinstance(expr, sp.Mul):
            factors = []
            for a in expr.args:
                factors.extend(a.args if isinstance(a, sp.Mul) else [a])
            return sp.Mul(*factors)
        return expr

    def _factor_repeats(self, expr: sp.Expr) -> sp.Expr:
        """Factor repeated terms in Add or Mul expressions."""
        if isinstance(expr, sp.Add):
            counts: Dict[sp.Expr, int] = {}
            for t in expr.args:
                counts[t] = counts.get(t, 0) + 1
            new_terms = [t if c == 1 else sp.Integer(c) * t for t, c in counts.items()]
            return sp.Add(*new_terms)

        if isinstance(expr, sp.Mul):
            counts = {}
            for t in expr.args:
                counts[t] = counts.get(t, 0) + 1
            new_factors = [t if c == 1 else (t ** sp.Integer(c)) for t, c in counts.items()]
            return sp.Mul(*new_factors)

        return expr

    def _sympify_safe(self, expr: str) -> Union[sp.Expr, str]:
        """
        Convert a SymPy-safe string into a SymPy expression.
        Keeps Grad/Eq/Ne available so axiom/rewriter outputs don't break.
        Returns original string on failure (caller can decide what to do).
        """
        try:
            return sp.sympify(
                expr,
                locals={
                    "Grad": Grad,
                    "Eq": sp.Eq,
                    "Ne": sp.Ne,
                },
            )
        except Exception as e:
            logger.warning(f"[Compressor] sympify failed: {e} (expr={expr!r})")
            return expr

    # =====================================================
    # Compression passes
    # =====================================================
    def compress_basic(self, expr_sym: Any) -> Any:
        """
        Basic compression:
        * Deduplication
        * Flatten Add/Mul
        Safe bypass for non-symbolic payloads.
        """
        if not hasattr(expr_sym, "args"):
            logger.debug(
                f"[Compressor] Basic bypass for non-symbolic payload ({type(expr_sym).__name__})"
            )
            return expr_sym

        expr_sym = self._dedup(expr_sym)
        expr_sym = expr_sym.replace(
            lambda e: isinstance(e, (sp.Add, sp.Mul)),
            self._flatten_ops,
        )
        return expr_sym

    def compress_advanced(self, expr_sym: Any) -> Any:
        """
        Advanced compression:
        * Dedup + flatten + repeat factoring
        * Preserves Grad(...) nodes (does not rewrite Grad itself)
        """
        if not hasattr(expr_sym, "args"):
            logger.debug(
                f"[Compressor] Advanced bypass for non-symbolic payload ({type(expr_sym).__name__})"
            )
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
    def normalize_compressed(self, expr: Union[str, sp.Expr, Any], mode: str = "basic") -> Any:
        """
        Normalize an expression string or SymPy tree using compression.
        mode = "basic" (default) or "advanced"
        """
        # Convert strings to symbolic form safely
        if isinstance(expr, str):
            expr_std = _glyph_to_sympy(expr)
            expr = self._sympify_safe(expr_std)

        # If sympify failed and left it as string, just return it unchanged.
        if isinstance(expr, str):
            return expr

        self.cache.clear()
        if mode == "basic":
            return self.compress_basic(expr)
        if mode == "advanced":
            return self.compress_advanced(expr)
        raise ValueError(f"Unknown compression mode: {mode!r}")


# =====================================================
# Convenience Singletons
# =====================================================
compressor = PhotonCompressor()
compressor_basic = compressor.compress_basic
compressor_adv = compressor.compress_advanced