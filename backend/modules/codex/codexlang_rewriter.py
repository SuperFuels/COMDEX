import re
from typing import Optional, Union, Any

class CodexLangRewriter:
    """
    Conservative symbolic simplifier and AST renderer for CodexLang expressions.

    - Soft mode keeps original surface form and only prunes trivial sub-terms.
    - Aggressive mode canonicalizes simple algebraic terms.
    - Includes structured rendering of symbolic ASTs (∧, ∨, ∀, ∃, →, etc).
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
            s = cls._rewrite_add_zero_soft(s)
            s = cls._rewrite_mul_one_soft(s)
            s = re.sub(r"¬\s*¬\s*", "", s)
            return s

        # Aggressive mode: allow stronger canonicalization (still cautious)
        s = cls._rewrite_add_zero_soft(s)
        s = cls._rewrite_mul_one_soft(s)
        s = re.sub(r"¬\s*¬\s*", "", s)

        # Basic commutativity for + when both sides are vars
        s = re.sub(r"\b([a-zA-Z_]\w*)\s*\+\s*0\b", r"\1 + 0", s)
        s = re.sub(r"\b0\s*\+\s*([a-zA-Z_]\w*)\b", r"\1 + 0", s)

        return s

    @staticmethod
    def _rewrite_add_zero_soft(s: str) -> str:
        s = re.sub(r"(?<![=<>])\b([a-zA-Z_]\w*)\s*\+\s*0\b", r"\1", s)
        s = re.sub(r"(?<![=<>])\b0\s*\+\s*([a-zA-Z_]\w*)\b", r"\1", s)
        return s

    @staticmethod
    def _rewrite_mul_one_soft(s: str) -> str:
        s = re.sub(r"\b([a-zA-Z_]\w*)\s*\*\s*1\b", r"\1", s)
        s = re.sub(r"\b1\s*\*\s*([a-zA-Z_]\w*)\b", r"\1", s)
        return s

    @classmethod
    def ast_to_codexlang(cls, symbolic_ast: Union[str, dict, list]) -> str:
        """
        Class-level fallback for AST → CodexLang rendering.
        Accepts:
        - Raw strings
        - Dict-style symbolic ASTs (used in ∀, ∃, →, ∧, etc)
        - Lists of terms
        """
        renderer = cls()
        return renderer.render_ast(symbolic_ast)

    from backend.modules.codex.collision_resolver import resolve_op

    def canonicalize_ops(self, tree: dict) -> dict:
        """
        Normalize all ops in the instruction tree into their canonical form.
        Uses `resolve_op`, which handles both simple mappings and collisions.
        """
        if not isinstance(tree, dict):
            return tree

        op = tree.get("op")
        if op:
            tree["op"] = resolve_op(op)

        # Recurse into args if present
        if "args" in tree and isinstance(tree["args"], list):
            tree["args"] = [
                self.canonicalize_ops(arg) if isinstance(arg, dict) else arg
                for arg in tree["args"]
            ]

        return tree

    def render_ast(self, ast: Any) -> str:
        """
        Recursively render structured AST into CodexLang.
        Supports symbolic logic trees like:
          ∀x. P(x) → Q(x)
          ¬(P ∧ Q) ∨ R
          equals(f(x), y)
        """
        if isinstance(ast, str):
            return self.simplify(ast)

        if isinstance(ast, list):
            return ", ".join([self.render_ast(item) for item in ast])

        if not isinstance(ast, dict):
            return self.simplify(str(ast))

        node_type = ast.get("type")

        if node_type == "forall":
            var = ast.get("var", "?")
            body = self.render_ast(ast.get("body"))
            return f"∀{var}. {body}"

        elif node_type == "exists":
            var = ast.get("var", "?")
            body = self.render_ast(ast.get("body"))
            return f"∃{var}. {body}"

        elif node_type == "implies":
            left = self.render_ast(ast.get("left"))
            right = self.render_ast(ast.get("right"))
            return f"{left} → {right}"

        elif node_type == "and":
            terms = [self.render_ast(t) for t in ast.get("terms", [])]
            return " ∧ ".join(terms)

        elif node_type == "or":
            terms = [self.render_ast(t) for t in ast.get("terms", [])]
            return " ∨ ".join(terms)

        elif node_type == "not":
            term = self.render_ast(ast.get("term"))
            return f"¬{term}"

        elif node_type == "equals":
            left = self.render_ast(ast.get("left"))
            right = self.render_ast(ast.get("right"))
            return f"{left} = {right}"

        elif node_type == "predicate":
            name = ast.get("name", "?")
            arg = self.render_ast(ast.get("arg", "?"))
            return f"{name}({arg})"

        elif node_type == "function":
            name = ast.get("name", "?")
            args = ", ".join([self.render_ast(a) for a in ast.get("args", [])])
            return f"{name}({args})"

        return self.simplify(str(ast))


# -------------------------
# 🔁 Rewrite Suggestion Engine
# -------------------------

def suggest_rewrite_candidates(ast: Union[str, dict]) -> list[dict]:
    """
    Suggest simple rewrites for a CodexLang AST.
    This supports contradiction fixing, simplification, or entropy reduction.

    Returns:
        List of suggestions like:
        { "reason": "Double negation", "rewrite": {...} }
    """
    suggestions = []

    if isinstance(ast, dict) and ast.get("type") == "not":
        inner = ast.get("term", {})
        if isinstance(inner, dict) and inner.get("type") == "not":
            # ¬(¬P) → P
            suggestions.append({
                "reason": "Double negation",
                "rewrite": inner.get("term")
            })

    if isinstance(ast, dict) and ast.get("type") == "and":
        terms = ast.get("terms", [])
        if "True" in terms or {"type": "constant", "value": "True"} in terms:
            simplified = [t for t in terms if t != "True" and t != {"type": "constant", "value": "True"}]
            if simplified:
                suggestions.append({
                    "reason": "Identity: P ∧ True → P",
                    "rewrite": {"type": "and", "terms": simplified}
                })

    # Future expansion: contradiction detection, entropy path scoring, goal match, etc.

    return suggestions

def extract_prediction_metadata(ast: Union[dict, str]) -> dict:
    """
    Extract embedded prediction metadata from an AST (if present).
    Returns:
        {
            "prediction": str | None,
            "sqi_score": float,
            "collapse_state": str
        }
    """
    if not isinstance(ast, dict):
        return {"prediction": None, "sqi_score": 0.0, "collapse_state": "unknown"}

    meta = ast.get("metadata", {})
    return {
        "prediction": meta.get("prediction", None),
        "sqi_score": float(meta.get("sqi_score", 0.0)),
        "collapse_state": meta.get("collapse_state", "unknown")
    }


def score_rewrite_candidate(candidate: dict) -> float:
    """
    Score a single rewrite candidate using embedded metadata.
    Higher score = better candidate.

    Uses:
    - SQI score as base
    - Collapse state bonuses
    - Future: prediction quality, entropy gain, etc.
    """
    metadata = extract_prediction_metadata(candidate)
    score = metadata["sqi_score"]

    if metadata["collapse_state"] == "collapsed":
        score += 0.2
    elif metadata["collapse_state"] == "entangled":
        score += 0.1

    return score