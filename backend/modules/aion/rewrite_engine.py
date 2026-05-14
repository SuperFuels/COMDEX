# -*- coding: utf-8 -*-
# backend/modules/aion/rewrite_engine.py
from __future__ import annotations
from typing import Any, Dict

# Try to use the CodexLang rewriter; fall back to no-op if unavailable.
try:
    from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
except Exception:
    class CodexLangRewriter:  # type: ignore
        @classmethod
        def simplify(cls, expr: str, mode: str = "soft") -> str:
            return expr

class RewriteEngine:
    """
    Minimal rewrite engine used by CodexExecutor for self-rewrite on contradictions.
    - Uses CodexLangRewriter in 'soft' mode by default (non-destructive).
    - Accepts either a plain Codex string in context['expr'|'codex_string'] or no expr at all.
    """

    def __init__(self, mode: str = "soft"):
        self.mode = mode

    def initiate_rewrite(self, reason: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ctx = context or {}
        # pull a string expression if present; otherwise just run a metadata-only rewrite
        expr = ctx.get("expr") or ctx.get("codex_string") or ""

        if isinstance(expr, str) and expr.strip():
            rewritten = CodexLangRewriter.simplify(expr, mode=self.mode)
            rules = ["soft:add_zero", "soft:mul_one", "soft:double_negation"]
        else:
            rewritten = expr
            rules = []

        return {
            "status": "ok",
            "reason": reason,
            "mode": self.mode,
            "original": expr,
            "rewritten": rewritten,
            "applied_rules": rules,
        }

    # Optional hook if later you want to rewrite a parsed tree shape
    def rewrite_tree(self, tree: Dict[str, Any]) -> Dict[str, Any]:
        # no-op for now; keep interface for future upgrades
        return tree