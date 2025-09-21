"""
Symatics Dispatcher
─────────────────────────────────────────────
Routes algebraic expressions (⊕, μ, ↔, etc.)
to their operator implementations.
"""

import logging
from typing import Any, Dict

from backend.modules.codex.logic_tree import LogicGlyph
from backend.symatics.symatics_rulebook import (
    op_superpose,
    op_measure,
    op_entangle,
    op_recurse,
    op_project,
    law_commutativity,
    law_associativity,
    collapse_rule,
)

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
        raise TypeError(f"Unsupported Symatics expression type: {type(expr)}")

    try:
        if op == "⊕":  # Superpose
            result = op_superpose(args[0], args[1], context)
        elif op == "μ":  # Measure
            inner = args[0]
            collapsed = collapse_rule(inner)
            result = op_measure(collapsed, context)
        elif op == "↔":  # Entangle
            result = op_entangle(args[0], args[1], context)
        elif op == "⟲":  # Recurse
            depth = getattr(expr, "depth", None) or (
                expr.get("depth") if isinstance(expr, dict) else 3
            )
            result = op_recurse(args[0], depth, context)
        elif op == "π":  # Project
            result = op_project(args[0], int(args[1]), context)
        else:
            raise ValueError(f"Unknown Symatics operator: {op}")

        # ── Apply algebra laws ──
        if op in {"⊕", "↔"} and len(args) >= 2:
            if not law_commutativity(op, args[0], args[1]):
                logger.warning(f"[Symatics] {op} failed commutativity law check.")

        if op == "⊕" and len(args) >= 3:
            if not law_associativity(op, args[0], args[1], args[2]):
                logger.warning("[Symatics] ⊕ failed associativity law check.")

        return result

    except Exception as e:
        logger.error(f"[Symatics] Evaluation failed: {e}")
        return {"status": "error", "error": str(e)}

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