# -*- coding: utf-8 -*-
# File: backend/symatics/symatics_dispatcher.py
"""
Symatics Dispatcher
─────────────────────────────────────────────
Routes algebraic expressions (⊕, μ, ↔, ⟲, π)
to their operator implementations via the
central registry bridge.

Enhancements:
 - Operator alias normalization (superpose → ⊕, entangle → ↔, etc.)
 - Context propagation for downstream traces
 - Fallback handling for unregistered ops
 - Extended post-law verification (commutativity, associativity, resonance, collapse, projection)
 - Consistent result envelope with engine="symatics"
"""

import logging
from typing import Any, Dict

from backend.modules.codex.logic_tree import LogicGlyph
from backend.symatics import symatics_rulebook as SR
from backend.core.registry_bridge import registry_bridge

# ──────────────────────────────
# Logger setup
# ──────────────────────────────
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# ──────────────────────────────
# Early registration of v0.3 physical operators (⟲, μ)
# ──────────────────────────────
def _symatics_resonance(a, b, context=None):
    """Resonance operator ⟲(a,b): applies resonance damping law."""
    SR.law_resonance_damping(a, b)
    return {
        "status": "ok",
        "engine": "symatics",
        "operator": "⟲",
        "args": [a, b],
        "result": f"Resonance({a},{b})",
        "context": context,
    }

def _symatics_measure(a, context=None):
    """Collapse operator μ(a): applies collapse conservation law."""
    SR.law_collapse_conservation(a)
    return {
        "status": "ok",
        "engine": "symatics",
        "operator": "μ",
        "args": [a],
        "result": f"Measure({a})",
        "context": context,
    }

try:
    registry_bridge.add("symatics:⟲", _symatics_resonance, namespace="symatics")
    registry_bridge.add("symatics:μ", _symatics_measure, namespace="symatics")
    logger.info("[Symatics] Registered ⟲ (resonance) and μ (collapse) operators.")
except Exception as e:
    logger.warning(f"[Symatics] Early registration failed: {e}")


# ──────────────────────────────
# Operator Alias Map
# ──────────────────────────────
_ALIAS_MAP = {
    "superpose": "⊕",
    "entangle": "↔",
    "resonate": "⟲",
    "measure": "μ",
    "project": "π",
}


def _normalize_op(op: str) -> str:
    """Normalize textual aliases to canonical Symatics symbols."""
    if not isinstance(op, str):
        return op
    return _ALIAS_MAP.get(op.strip(), op.strip())


# ──────────────────────────────
# Dispatcher
# ──────────────────────────────
def evaluate_symatics_expr(expr: Any, context: Dict = None) -> Dict[str, Any]:
    """
    Evaluate a Symatics expression.

    Accepts:
      • LogicGlyph object
      • dict with {"op"/"operator": "...", "args": [...]}

    Returns:
      dict(status, result, engine="symatics", operator, args, context)
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
        return {
            "status": "error",
            "engine": "symatics",
            "error": f"Unsupported Symatics expression type: {type(expr)}",
        }

    op = _normalize_op(op)

    # ✅ Registry check before execution
    key = f"symatics:{op}"
    if not hasattr(registry_bridge, "has_handler") or not registry_bridge.has_handler(key):
        logger.warning(f"[Symatics] Operator {op} not found in registry; using passthrough.")
        return {
            "status": "ok",
            "engine": "symatics",
            "operator": op,
            "args": args,
            "note": "unregistered op passthrough",
            "context": context,
        }

    try:
        # ✅ Canonical registry execution
        result = registry_bridge.resolve_and_execute(key, *args, context=context)

        # Initialize Codex trace handle
        from backend.modules.codex.codex_trace import CodexTrace
        trace = CodexTrace()  # global singleton handle

        # ────────────────────────────────────────────────
        # 🔍 v0.3 theorem verification + trace emission
        # ────────────────────────────────────────────────
        try:
            law_check = SR.check_all_laws(op, *args, context=context)
            result["law_check"] = law_check

            trace.log({
                "type": "theorem",
                "engine": "symatics",
                "action": "law_check",
                "operator": op,
                "timestamp": law_check.get("timestamp"),
                "summary": law_check.get("summary"),
                "violations": law_check.get("violations"),
                "context": context or {},
            })

            # Direct ledger persistence (mirrors theorem_writer)
            try:
                import json, os
                os.makedirs("docs/rfc", exist_ok=True)
                with open("docs/rfc/theorem_ledger.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "type": "theorem",
                        "engine": "symatics",
                        "action": "law_check",
                        "operator": op,
                        "timestamp": law_check.get("timestamp"),
                        "summary": law_check.get("summary"),
                        "violations": law_check.get("violations"),
                        "context": context or {},
                    }, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.warning(f"[SymaticsLedger] Failed to append ledger: {e}")

        except Exception as e:
            logger.warning(f"[SymaticsTrace] failed to emit law_check: {e}")

        # ────────────────────────────────────────────────
        # 🔹 Post-evaluation Symatics Law Validation
        # ────────────────────────────────────────────────
        if op in {"⊕", "↔"} and len(args) >= 2:
            if not SR.law_commutativity(op, args[0], args[1]):
                logger.warning(f"[Symatics] {op} failed commutativity law check.")
        if op == "⊕" and len(args) >= 3:
            if not SR.law_associativity(op, args[0], args[1], args[2]):
                logger.warning("[Symatics] ⊕ failed associativity law check.")
        if op == "⟲" and len(args) >= 2:
            SR.law_resonance_damping(args[0], args[1])   # ✅ v0.3 resonance
        if op == "μ":
            SR.law_collapse_conservation(args[0])        # ✅ v0.3 collapse
        if op == "π":
            SR.law_projection_consistency(expr)

    except Exception as e:
        logger.error(f"[SymaticsDispatcher] evaluation failed: {e}")
        law_check = SR.check_all_laws(op, *args, context=context)
        CodexTrace.log("law_check", law_check)

        # ────────────────────────────────────────────────
        # 🔹 Post-evaluation Symatics Law Validation
        # ────────────────────────────────────────────────
        try:
            law_result = SR.check_all_laws(op, *args, context=context)
            result["law_check"] = law_result

            summary = law_result.get("summary", "")
            violations = law_result.get("violations", [])
            if violations:
                logger.warning(f"[Symatics] Law violations detected for {op}: {violations} ({summary})")
            else:
                logger.debug(f"[Symatics] {op} → all {summary}")
        except Exception as e:
            logger.warning(f"[Symatics] Law validation skipped for {op}: {e}")
            result["law_check"] = {
                "symbol": op,
                "summary": "law check skipped",
                "violations": [str(e)]
            }

        # 🧩 Ensure consistent envelope
        if isinstance(result, dict):
            result.setdefault("engine", "symatics")
            result.setdefault("operator", op)
            result.setdefault("args", args)
            result.setdefault("context", context)
        else:
            result = {
                "status": "ok",
                "engine": "symatics",
                "operator": op,
                "args": args,
                "context": context,
                "result": result,
            }

        return result

    except Exception as e:
        logger.error(f"[Symatics] Evaluation failed: {e}", exc_info=True)
        return {
            "status": "error",
            "engine": "symatics",
            "operator": op,
            "args": args,
            "error": f"SymaticsExecutionError: {str(e)}",
            "context": context,
        }


# ──────────────────────────────
# Operator Detection Helper
# ──────────────────────────────
def is_symatics_operator(op: Any) -> bool:
    """Return True if the operator is one of the Symatics algebra symbols."""
    sym_ops = {"⊕", "μ", "↔", "⟲", "π"}
    if hasattr(op, "operator"):  # glyph object
        return op.operator in sym_ops
    if isinstance(op, str):      # raw string glyph
        return any(sym in op for sym in sym_ops) or op.strip() in _ALIAS_MAP
    return False


# ──────────────────────────────
# CLI Demo
# ──────────────────────────────
if __name__ == "__main__":
    print("Demo: evaluating ⊕ with args [1, 2]")
    result = evaluate_symatics_expr({"op": "⊕", "args": [1, 2]})
    print("Result:", result)

    print("Demo: evaluating alias 'superpose'")
    alias = evaluate_symatics_expr({"op": "superpose", "args": [1, 2]})
    print("Result:", alias)

    print("Demo: invalid operator")
    bad = evaluate_symatics_expr({"op": "??", "args": [1]})
    print("Result:", bad)

# ──────────────────────────────
# ✅ v0.3 Physical Operator Implementations
# ──────────────────────────────
def symatics_resonance(a, b, context=None):
    """
    Physical resonance operator ⟲(a,b)
    Applies resonance damping law and returns structured result.
    """
    try:
        SR.law_resonance_damping(a, b)
        result = f"Resonance({a},{b})"
    except Exception as e:
        result = f"ResonanceError({e})"
    return {
        "status": "ok",
        "engine": "symatics",
        "operator": "⟲",
        "args": [a, b],
        "result": result,
        "context": context,
    }


def symatics_measure(a, context=None):
    """
    Measurement operator μ(a)
    Applies collapse conservation law and returns structured result.
    """
    try:
        SR.law_collapse_conservation(a)
        result = f"Measure({a})"
    except Exception as e:
        result = f"MeasureError({e})"
    return {
        "status": "ok",
        "engine": "symatics",
        "operator": "μ",
        "args": [a],
        "result": result,
        "context": context,
    }


# ──────────────────────────────
# ✅ Register Physical Operators in Runtime Registry (always executes on import)
# ──────────────────────────────
try:
    registry_bridge.register("symatics:⟲", symatics_resonance)
    registry_bridge.register("symatics:μ", symatics_measure)
    logger.info("[Symatics] Registered ⟲ (resonance) and μ (collapse) operators.")
except Exception as e:
    logger.warning(f"[Symatics] Failed to register physical operators: {e}")