# ===============================
# 📁 backend/modules/codex/codexlang_evaluator.py
# ===============================
from __future__ import annotations
from typing import Tuple, Any, Dict
import ast
import math

# Allow only a small set of nodes and operators for safety
_ALLOWED_NODES = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant, ast.Name, ast.Call, ast.Load,
    ast.Pow, ast.Mult, ast.Div, ast.Add, ast.Sub, ast.Mod, ast.USub, ast.UAdd, ast.FloorDiv, ast.Tuple
}

_ALLOWED_FUNCS = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "exp": math.exp, "sqrt": math.sqrt,
    "abs": abs, "min": min, "max": max, "round": round
}

_ALLOWED_NAMES = {
    "pi": math.pi, "e": math.e
}

def _safe(node: ast.AST) -> None:
    if type(node) not in _ALLOWED_NODES:
        raise ValueError(f"Disallowed syntax: {type(node).__name__}")
    for child in ast.iter_child_nodes(node):
        _safe(child)

def evaluate_codexlang(expr: str, env: Dict[str, Any] | None = None) -> Tuple[str | None, str | None]:
    """
    Evaluate a tiny arithmetic/CodexLang subset safely.
    Returns: (render, error)
    - render: canonical string of the computed result (e.g., '3.14159')
    - error:  error message if any
    """
    expr = (expr or "").strip()
    if not expr:
        return "", None

    try:
        parsed = ast.parse(expr, mode="eval")
        _safe(parsed)
        # Build evaluation environment
        scope: Dict[str, Any] = {}
        scope.update(_ALLOWED_FUNCS)
        scope.update(_ALLOWED_NAMES)
        if env:
            # Allow simple scalar variables only
            for k, v in env.items():
                if isinstance(v, (int, float)):
                    scope[k] = v
        val = eval(compile(parsed, "<codexlang>", "eval"), {"__builtins__": {}}, scope)
        # pretty print number-like results
        if isinstance(val, (int, float)):
            return f"{val:.6g}", None
        return str(val), None
    except Exception as e:
        return None, str(e)