from typing import List, Dict, Optional, Any
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.codex.codexlang_rewriter import suggest_rewrite_candidates
from backend.modules.codex.codex_ast_encoder import parse_codexlang_to_ast
import logging

logger = logging.getLogger(__name__)


# ----------------------------
# Minimal fallback parser (for simple propositional inputs like "A ∧ ¬A")
# ----------------------------

_UNI_MAP = {
    "¬": "NOT",
    "~": "NOT",
    "∧": "AND",
    "/\\": "AND",
    "∨": "OR",
    "\\/": "OR",
    "→": "IMPLIES",
    "->": "IMPLIES",
    "↔": "IFF",
    "<->": "IFF",
    "(": "LPAREN",
    ")": "RPAREN",
}

def _tokenize_prop(s: str) -> List[str]:
    s = (s or "").strip()
    if not s:
        return []
    # normalize multi-char operators first
    s = s.replace("<->", " ↔ ").replace("->", " → ")
    s = s.replace("/\\", " ∧ ").replace("\\/", " ∨ ")
    for ch in ["¬", "∧", "∨", "→", "↔", "(", ")"]:
        s = s.replace(ch, f" {ch} ")
    parts = [p for p in s.split() if p]
    out: List[str] = []
    for p in parts:
        out.append(_UNI_MAP.get(p, p))
    return out

class _TokStream:
    def __init__(self, toks: List[str]):
        self.toks = toks
        self.i = 0

    def peek(self) -> Optional[str]:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def pop(self) -> Optional[str]:
        t = self.peek()
        if t is not None:
            self.i += 1
        return t

def _atom(name: str) -> Dict[str, Any]:
    return {"type": "atom", "name": name}

# Precedence: NOT > AND > OR > IMPLIES > IFF
def _parse_prop_expr(ts: _TokStream) -> Dict[str, Any]:
    return _parse_iff(ts)

def _parse_iff(ts: _TokStream) -> Dict[str, Any]:
    left = _parse_implies(ts)
    while ts.peek() == "IFF":
        ts.pop()
        right = _parse_implies(ts)
        left = {"type": "iff", "left": left, "right": right}
    return left

def _parse_implies(ts: _TokStream) -> Dict[str, Any]:
    left = _parse_or(ts)
    while ts.peek() == "IMPLIES":
        ts.pop()
        right = _parse_or(ts)
        left = {"type": "implies", "left": left, "right": right}
    return left

def _parse_or(ts: _TokStream) -> Dict[str, Any]:
    left = _parse_and(ts)
    while ts.peek() == "OR":
        ts.pop()
        right = _parse_and(ts)
        left = {"type": "or", "left": left, "right": right}
    return left

def _parse_and(ts: _TokStream) -> Dict[str, Any]:
    left = _parse_not(ts)
    while ts.peek() == "AND":
        ts.pop()
        right = _parse_not(ts)
        left = {"type": "and", "left": left, "right": right}
    return left

def _parse_not(ts: _TokStream) -> Dict[str, Any]:
    if ts.peek() == "NOT":
        ts.pop()
        child = _parse_not(ts)
        return {"type": "not", "child": child}
    return _parse_primary(ts)

def _parse_primary(ts: _TokStream) -> Dict[str, Any]:
    t = ts.peek()
    if t == "LPAREN":
        ts.pop()
        node = _parse_prop_expr(ts)
        if ts.pop() != "RPAREN":
            raise ValueError("missing ')'")
        return node
    if t is None:
        raise ValueError("unexpected end of input")
    ts.pop()
    # treat anything else as an atom symbol
    return _atom(str(t))

def _fallback_parse_prop(s: str) -> Dict[str, Any]:
    toks = _tokenize_prop(s)
    ts = _TokStream(toks)
    node = _parse_prop_expr(ts)
    if ts.peek() is not None:
        raise ValueError(f"unexpected token: {ts.peek()}")
    return node


# ----------------------------
# AST utilities
# ----------------------------
def ast_equal(a: Any, b: Any) -> bool:
    """
    Structural AST equality check (deep compare for dicts + lists).
    """
    if type(a) != type(b):
        return False

    if isinstance(a, dict):
        if a.get("type") != b.get("type"):
            return False
        keys = set(a.keys()) | set(b.keys())
        for k in keys:
            if not ast_equal(a.get(k), b.get(k)):
                return False
        return True

    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(ast_equal(x, y) for x, y in zip(a, b))

    return a == b


def is_negation_of(a: Optional[Dict], b: Optional[Dict]) -> bool:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
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
    Goal-local contradiction detector.
    Only flags patterns that are contradictions by themselves (e.g. A ∧ ¬A).
    """
    if not isinstance(ast, dict):
        return None

    node_type = ast.get("type")

    if node_type == "and":
        left, right = ast.get("left"), ast.get("right")
        if is_negation_of(left, right) or is_negation_of(right, left):
            return "Contradiction: A ∧ ¬A"

    # recurse
    for k in ("left", "right", "child"):
        v = ast.get(k)
        if isinstance(v, dict):
            r = detect_contradictions(v)
            if r:
                return r

    v = ast.get("args")
    if isinstance(v, list):
        for sub in v:
            if isinstance(sub, dict):
                r = detect_contradictions(sub)
                if r:
                    return r

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

    ast: Optional[Dict[str, Any]] = None
    used_fallback = False

    # 1) Prefer real CodexLang parser
    try:
        ast = parse_codexlang_to_ast(goal)
    except Exception as e:
        # 2) Fallback for simple propositional Unicode input
        try:
            ast = _fallback_parse_prop(goal)
            used_fallback = True
        except Exception:
            logger.error(f"[LeanSuggest] Parse error: {e}")
            suggestions.append("sorry")
            return suggestions

    contradiction = detect_contradictions(ast)

    # If goal itself is A ∧ ¬A, suggest simp/aesop first
    if contradiction:
        logger.warning(f"[LeanSuggest] ⚠️ Goal-local contradiction detected: {contradiction}")
        suggestions.extend(["simp", "aesop"])
        return suggestions

    # context-level contradiction: find A and ¬A in context
    try:
        ctx_asts: List[Dict[str, Any]] = []
        for c in context:
            try:
                ctx_asts.append(parse_codexlang_to_ast(c))
            except Exception:
                ctx_asts.append(_fallback_parse_prop(c))
        for i in range(len(ctx_asts)):
            for j in range(i + 1, len(ctx_asts)):
                if is_negation_of(ctx_asts[i], ctx_asts[j]):
                    suggestions.append("contradiction")
                    raise StopIteration
    except StopIteration:
        pass
    except Exception:
        pass

    # normal goal-shape tactics (works for fallback AST too)
    node_type = (ast or {}).get("type")
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

    # rewrite suggestions only when we have a real CodexLang AST (skip for fallback)
    if not used_fallback:
        try:
            rewrite_opts = suggest_rewrite_candidates(ast)
            if rewrite_opts:
                best = rewrite_opts[0]
                suggestions.append(f"rewrite {best.get('label', '...')}")
                CodexTrace.log_prediction(
                    glyph="⊥",
                    gtype="rewrite_candidate",
                    best_prediction=best,
                )
        except Exception:
            pass

    if not suggestions:
        suggestions.append("sorry")
    return suggestions