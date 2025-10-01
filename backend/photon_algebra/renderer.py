# File: backend/photon_algebra/renderer.py
"""
Photon Renderer
---------------
Pretty-printer for Photon algebra expressions.
Ensures all states are converted to strings safely.
"""

# backend/photon_algebra/renderer.py

# Map domain:op strings to pretty glyphs
OP_GLYPHS = {
    "quantum:⊗": "⊗",
    "symatics:⊕": "⊕",
    "photon:⊕": "⊕",
    "photon:⊗": "⊗",
    "photon:⊖": "⊖",
    "photon:¬": "¬",
    "photon:↔": "↔",
    "photon:★": "★",
    "photon:∅": "∅",
}

def render_photon(expr) -> str:
    if expr is None:
        return "∅"

    if isinstance(expr, (str, int, float)):
        return str(expr)

    if isinstance(expr, dict):
        if "opcode" in expr:
            op = expr["opcode"]
            args = expr.get("args", [])
            rendered_args = [render_photon(a) for a in args]
            # Use glyph if known
            op_display = OP_GLYPHS.get(op, op)
            return f"({f' {op_display} '.join(rendered_args)})"

        op = expr.get("op")

        if "state" in expr:
            return f"{op}({render_photon(expr['state'])})"

        if "states" in expr:
            states = [render_photon(s) for s in expr["states"]]
            return f"({f' {op} '.join(states)})"

        return f"{op}()"

    if isinstance(expr, (list, tuple)):
        return "(" + ", ".join(render_photon(e) for e in expr) + ")"

    return str(expr)