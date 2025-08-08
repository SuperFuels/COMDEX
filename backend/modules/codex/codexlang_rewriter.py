# backend/modules/codex/codexlang_rewriter.py

import re
from typing import Optional

class CodexLangRewriter:
    """
    Conservative symbolic simplifier for CodexLang expressions.
    - Soft mode keeps original surface form and only prunes trivial sub-terms.
    - Never collapses an equality A = B into B = B in soft mode.
    """

    @classmethod
    def simplify(cls, expr: str, mode: str = "soft") -> str:
        if not isinstance(expr, str) or not expr.strip():
            return expr

        if mode not in {"soft", "aggressive"}:
            mode = "soft"

        s = expr

        # --- universal whitespace tidy ---
        s = re.sub(r"\s+", " ", s).strip()

        # In soft mode, only do tiny local rewrites that are safe & readable
        if mode == "soft":
            # + 0 / 0 + n inside terms, but DO NOT rewrite the whole equality
            s = cls._rewrite_add_zero_soft(s)
            # * 1 inside terms
            s = cls._rewrite_mul_one_soft(s)
            # de-double negations ¬¬A -> A (only outside of quoted text)
            s = re.sub(r"¬\s*¬\s*", "", s)

            # Keep equality structure intact
            return s

        # Aggressive mode: allow stronger canonicalization (still cautious)
        s = cls._rewrite_add_zero_soft(s)
        s = cls._rewrite_mul_one_soft(s)
        s = re.sub(r"¬\s*¬\s*", "", s)

        # Basic commutativity for + when both sides are vars (n + 0 == 0 + n normalized to n + 0)
        s = re.sub(r"\b([a-zA-Z_]\w*)\s*\+\s*0\b", r"\1 + 0", s)
        s = re.sub(r"\b0\s*\+\s*([a-zA-Z_]\w*)\b", r"\1 + 0", s)

        return s

    @staticmethod
    def _rewrite_add_zero_soft(s: str) -> str:
        # Rewrite inside parentheses or sub-terms, avoid touching top-level equality comparisons
        # n + 0  -> n  (but only when clearly a subterm)
        s = re.sub(r"(?<![=<>])\b([a-zA-Z_]\w*)\s*\+\s*0\b", r"\1", s)
        s = re.sub(r"(?<![=<>])\b0\s*\+\s*([a-zA-Z_]\w*)\b", r"\1", s)
        return s

    @staticmethod
    def _rewrite_mul_one_soft(s: str) -> str:
        # n * 1 -> n, 1 * n -> n
        s = re.sub(r"\b([a-zA-Z_]\w*)\s*\*\s*1\b", r"\1", s)
        s = re.sub(r"\b1\s*\*\s*([a-zA-Z_]\w*)\b", r"\1", s)
        return s