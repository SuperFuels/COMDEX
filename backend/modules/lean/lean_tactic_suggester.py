# backend/modules/lean/lean_tactic_suggester.py

from typing import List, Dict, Optional
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.codex.codex_lang_rewriter import suggest_rewrite_candidates
from backend.modules.codex.codex_ast_encoder import parse_codexlang_to_ast
import logging

logger = logging.getLogger(__name__)

def detect_contradictions(ast: Dict) -> Optional[str]:
    """
    Simple AST-based contradiction detector.
    Looks for patterns like: ¬A ∧ A or A → ¬A
    """
    node_type = ast.get("type")
    if node_type == "and":
        left, right = ast.get("left"), ast.get("right")
        if is_negation_of(left, right) or is_negation_of(right, left):
            return "Contradiction: A ∧ ¬A"
    if node_type == "implies":
        premise, conclusion = ast.get("left"), ast.get("right")
        if is_negation_of(premise, conclusion):
            return "Contradiction: A → ¬A"
    if node_type == "iff":
        left, right = ast.get("left"), ast.get("right")
        if is_negation_of(left, right):
            return "Contradiction: A ↔ ¬A"
    # recursive check
    for k in ("left", "right", "child"):
        if isinstance(ast.get(k), dict):
            reason = detect_contradictions(ast[k])
            if reason:
                return reason
    return None

def is_negation_of(a: Dict, b: Dict) -> bool:
    """
    Returns True if a == ¬b or vice versa
    """
    if a.get("type") == "not" and a.get("child") == b:
        return True
    if b.get("type") == "not" and b.get("child") == a:
        return True
    return False

def suggest_tactics(goal: str, context: List[str]) -> List[str]:
    """
    Suggest tactics to prove a goal from current context.
    Inspects logic, detects contradiction, and proposes rewrites.
    """
    logger.info(f"[LeanSuggest] Goal: {goal}")
    suggestions = []

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
                    best_prediction=best
                )
        else:
            node_type = ast.get("type")
            if node_type in ("forall", "lambda"):
                suggestions.extend(["intro", "assume"])
            if node_type == "implies":
                suggestions.extend(["intro", "apply", "assumption"])
            if node_type == "and":
                suggestions.extend(["split", "assumption"])
            if node_type == "or":
                suggestions.extend(["left", "right", "cases"])
            if goal in context:
                suggestions.append("exact")
    except Exception as e:
        logger.error(f"[LeanSuggest] Parse error: {e}")
        suggestions.append("sorry")  # fallback

    if not suggestions:
        suggestions.append("sorry")
    return suggestions