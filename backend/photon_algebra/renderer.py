# File: backend/photon_algebra/renderer.py
"""
Photon Renderer
---------------
Pretty-printer for Photon algebra expressions.
Ensures all states are converted to strings safely.
"""

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
    "photon:⊤": "⊤",
    "photon:⊥": "⊥",
}

# Define sets for special rendering rules
INFIX_OPS = {"⊕", "⊗", "↔", "⊖", "≈", "⊂"}
NULLARY_OPS = {"∅", "⊤", "⊥"}
UNARY_OPS = {"¬", "★"}


def render_photon(expr) -> str:
    if expr is None:
        return "∅"

    if isinstance(expr, (str, int, float)):
        return str(expr)

    if isinstance(expr, dict):
        # Legacy instruction dicts with 'opcode'
        if "opcode" in expr:
            op = expr["opcode"].split(":")[-1]
            args = expr.get("args", [])
            rendered_args = [render_photon(a) for a in args]

            # Unary ops
            if op in UNARY_OPS and rendered_args:
                inner = rendered_args[0]
                # parenthesize compound
                if isinstance(args[0], dict) and ("states" in args[0] or "state" in args[0]):
                    inner = f"({inner})"
                return f"{op}{inner}"

            # Nullary
            if op in NULLARY_OPS:
                return op

            # Infix ops
            if op in INFIX_OPS:
                return "(" + f" {op} ".join(rendered_args) + ")"

            # Fallback
            return f"{op}(" + ", ".join(rendered_args) + ")"

        # Photon AST dicts with 'op'
        op = expr.get("op")

        # Nullary
        if op in NULLARY_OPS:
            return op

        # Unary
        if "state" in expr:
            inner = render_photon(expr["state"])
            if isinstance(expr["state"], dict) and ("states" in expr["state"] or "state" in expr["state"]):
                inner = f"({inner})"
            return f"{op}{inner}"

        # N-ary
        if "states" in expr:
            parts = [render_photon(s) for s in expr["states"]]
            if op in INFIX_OPS:
                return "(" + f" {op} ".join(parts) + ")"
            return f"{op}(" + ", ".join(parts) + ")"

        # Fallback
        return str(op)

    if isinstance(expr, (list, tuple)):
        return "(" + ", ".join(render_photon(e) for e in expr) + ")"

    return str(expr)