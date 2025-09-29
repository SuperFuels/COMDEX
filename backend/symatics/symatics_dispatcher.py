# -*- coding: utf-8 -*-
# File: backend/symatics/symatics_dispatcher.py
"""
Symatics Dispatcher
─────────────────────────────────────────────
Routes algebraic expressions (⊕, μ, ↔, ⟲, π)
to their operator implementations via the
central registry bridge.
"""

import logging
from typing import Any, Dict

from backend.modules.codex.logic_tree import LogicGlyph
from backend.symatics import symatics_rulebook as SR
from backend.core.registry_bridge import registry_bridge


logger = logging.getLogger(__name__)


# ──────────────────────────────
# Dispatcher
# ──────────────────────────────

def evaluate_symatics_expr(expr: Any, context: Dict = None) -> Dict[str, Any]:
    """
    Evaluate a Symatics expression.

    Accepts:
      • LogicGlyph object
      • dict with {"op"/"operator": "...", "args": [...]}
    """
    context = context or {}

    # 🔄 Normalize input
    if isinstance(expr, LogicGlyph):
        op = expr.operator
        args = expr.args or []
    elif isinstance(expr, dict):
        op = expr.get("op") or expr.get("operator")
        args = expr.get("args", [])
    else:
        return {"status": "error", "error": f"Unsupported Symatics expression type: {type(expr)}"}

    try:
        # ✅ Route via registry (canonical symatics:* key)
        key = f"symatics:{op}"
        result = registry_bridge.resolve_and_execute(key, *args, context=context)

        # ── Apply algebra laws (post-checks only, log warnings) ──
        if op in {"⊕", "↔"} and len(args) >= 2:
            if not SR.law_commutativity(op, args[0], args[1]):
                logger.warning(f"[Symatics] {op} failed commutativity law check.")

        if op == "⊕" and len(args) >= 3:
            if not SR.law_associativity(op, args[0], args[1], args[2]):
                logger.warning("[Symatics] ⊕ failed associativity law check.")

        return result

    except Exception as e:
        logger.error(f"[Symatics] Evaluation failed: {e}")
        return {"status": "error", "error": f"SymaticsExecutionError: {str(e)}"}


# ──────────────────────────────
# Operator Detection Helper
# ──────────────────────────────

def is_symatics_operator(op: Any) -> bool:
    """Return True if the operator is one of the Symatics algebra symbols."""
    sym_ops = {"⊕", "μ", "↔", "⟲", "π"}
    if hasattr(op, "operator"):  # glyph object
        return op.operator in sym_ops
    if isinstance(op, str):      # raw string glyph
        return any(sym in op for sym in sym_ops)
    return False

if __name__ == "__main__":
    print("Demo: evaluating ⊕ with args [1, 2]")
    result = evaluate_symatics_expr({"op": "⊕", "args": [1, 2]})
    print("Result:", result)

    print("Demo: invalid operator")
    bad = evaluate_symatics_expr({"op": "??", "args": [1]})
    print("Result:", bad)