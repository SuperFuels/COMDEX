# File: backend/modules/lean/lean_tactic_suggester.py

from typing import List, Dict, Optional
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.codex.codexlang_rewriter import suggest_rewrite_candidates
from backend.modules.codex.codex_ast_encoder import parse_codexlang_to_ast
import logging

logger = logging.getLogger(__name__)


# ----------------------------
# AST utilities
# ----------------------------
def ast_equal(a: Dict, b: Dict) -> bool:
    """
    Structural AST equality check (deep dict compare).
    """
    if not isinstance(a, dict) or not isinstance(b, dict):
        return a == b
    if a.get("type") != b.get("type"):
        return False
    for k in set(a.keys()) | set(b.keys()):
        if not ast_equal(a.get(k), b.get(k)):
            return False
    return True


def is_negation_of(a: Dict, b: Dict) -> bool:
    """
    Returns True if a == ¬b or vice versa.
    """
    if a.get("type") == "not" and ast_equal(a.get("child"), b):
        return True
    if b.get("type") == "not" and ast_equal(b.get("child"), a):
        return True
    return False


# ----------------------------
# Contradiction detection
# ----------------------------
def detect_contradictions(ast: Dict) -> Optional[str]:
    """
    Simple AST-based contradiction detector.
    Looks for patterns like: ¬A ∧ A, A -> ¬A, A ↔ ¬A.
    """
    if not isinstance(ast, dict):
        return None

    node_type = ast.get("type")

    if node_type == "and":
        left, right = ast.get("left"), ast.get("right")
        if is_negation_of(left, right) or is_negation_of(right, left):
            return "Contradiction: A ∧ ¬A"

    if node_type == "implies":
        premise, conclusion = ast.get("left"), ast.get("right")
        if is_negation_of(premise, conclusion):
            return "Contradiction: A -> ¬A"

    if node_type == "iff":
        left, right = ast.get("left"), ast.get("right")
        if is_negation_of(left, right):
            return "Contradiction: A ↔ ¬A"

    # recursive check across children
    for k in ("left", "right", "child", "args"):
        v = ast.get(k)
        if isinstance(v, dict):
            reason = detect_contradictions(v)
            if reason:
                return reason
        elif isinstance(v, list):
            for sub in v:
                if isinstance(sub, dict):
                    reason = detect_contradictions(sub)
                    if reason:
                        return reason

    return None


# ----------------------------
# Tactic suggestion engine
# ----------------------------
def suggest_tactics(goal: str, context: List[str]) -> List[str]:
    """
    Suggest tactics to prove a goal from current context.
    Inspects logic, detects contradictions, and proposes rewrites.
    """
    logger.info(f"[LeanSuggest] Goal: {goal}")
    suggestions: List[str] = []

    try:
        ast = parse_codexlang_to_ast(goal)
        contradiction = detect_contradictions(ast)

        if contradiction:
            logger.warning(f"[LeanSuggest] ⚠️ Contradiction detected: {contradiction}")
            suggestions.append("contradiction")

            # Auto-repair attempt (optional fallback)
            rewrite_opts = suggest_rewrite_candidates(ast)
            if rewrite_opts:
                best = rewrite_opts[0]
                suggestions.append(f"rewrite {best.get('label', '...')}")
                CodexTrace.log_prediction(
                    glyph="⊥",
                    gtype="contradiction",
                    best_prediction=best,
                )
        else:
            node_type = ast.get("type")
            if node_type in ("forall", "lambda"):
                suggestions.extend(["intro", "assume"])
            elif node_type == "implies":
                suggestions.extend(["intro", "apply", "assumption"])
            elif node_type == "and":
                suggestions.extend(["split", "assumption"])
            elif node_type == "or":
                suggestions.extend(["left", "right", "cases"])
            elif node_type == "exists":
                suggestions.extend(["use", "exists.intro"])
            elif node_type == "eq":
                suggestions.extend(["refl", "rw", "simp"])

            # context check (structural equality if possible)
            try:
                ctx_asts = [parse_codexlang_to_ast(c) for c in context]
                if any(ast_equal(ast, c) for c in ctx_asts):
                    suggestions.append("exact")
            except Exception:
                if goal in context:
                    suggestions.append("exact")

    except Exception as e:
        logger.error(f"[LeanSuggest] Parse error: {e}")
        suggestions.append("sorry")  # fallback

    if not suggestions:
        suggestions.append("sorry")

    return suggestions