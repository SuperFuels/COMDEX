# backend/tools/photon_pp.py

from typing import Any, List

def pp(expr: Any) -> str:
    """Readable infix-ish form for quick debugging (not a full parser)."""
    if not isinstance(expr, dict):
        return str(expr)
    op = expr.get("op")
    if op == "⊕":
        return "(" + " ⊕ ".join(pp(s) for s in expr.get("states", [])) + ")"
    if op == "⊗":
        return "(" + " ⊗ ".join(pp(s) for s in expr.get("states", [])) + ")"
    if op == "⊖":
        st = expr.get("states", [])
        return "(" + " ⊖ ".join(pp(s) for s in st) + ")"
    if op == "↔":
        st = expr.get("states", [])
        return "(" + " ↔ ".join(pp(s) for s in st) + ")"
    if op == "★":
        return "★" + pp(expr.get("state"))
    if op == "¬":
        return "¬" + pp(expr.get("state"))
    if op == "∅":
        return "∅"
    # fallback generic
    if "states" in expr:
        return f"{op}(" + ", ".join(pp(s) for s in expr["states"]) + ")"
    if "state" in expr:
        return f"{op}(" + pp(expr["state"]) + ")"
    return str(expr)