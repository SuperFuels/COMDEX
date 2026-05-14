"""
Photon Axioms Module
--------------------
Defines the primitive laws of the Photon symbolic system (replacement for binary).
These axioms serve as the foundation for rewriting, theorem proving, and execution.
"""

from typing import Dict, Tuple

# Primitive glyphs in Photon space
GLYPHS = {
    "ADD": "⊕",
    "SUB": "⊖",
    "MUL": "⊗",
    "DIV": "/",
    "EQ": "↔",
    "NEQ": "!=",
    "GRAD": "∇",
    "MUTATE": "⟲",
    "MILESTONE": "✦",
    "TRIGGER": "->",
}

# --- Glyph -> Sympy translation rules ---
# backend/photon/axioms.py

import re  # <-- add this

def _glyph_to_sympy(expr: str) -> str:
    """
    Convert a glyph expression into a Sympy-safe string.
    Handles special cases (↔, !=, ∇) -> Eq/Ne/Grad().
    """
    expr = (expr or "").strip()

    # basic glyph algebra -> sympy operators
    expr = expr.replace("⊕", "+")
    expr = expr.replace("⊗", "*")
    expr = expr.replace("⊖", "-")

    # ✅ convert ALL gradient forms, not just leading one
    # ∇(x) -> Grad(x)
    expr = re.sub(r"∇\s*\(", "Grad(", expr)

    # (optional) bare ∇x -> Grad(x) for simple identifiers
    expr = re.sub(r"\b∇\s*([A-Za-z_]\w*)\b", r"Grad(\1)", expr)

    if "↔" in expr:
        lhs, rhs = expr.split("↔", 1)
        return f"Eq({lhs.strip()}, {rhs.strip()})"
    if "!=" in expr:
        lhs, rhs = expr.split("!=", 1)
        return f"Ne({lhs.strip()}, {rhs.strip()})"

    return expr


# Axiom format: (glyph_pattern, glyph_replacement, description)
AXIOMS: Dict[str, Tuple[str, str, str]] = {
    # Arithmetic Laws
    "comm_add": ("a ⊕ b", "b ⊕ a", "Commutativity of ⊕"),
    "assoc_add": ("(a ⊕ b) ⊕ c", "a ⊕ (b ⊕ c)", "Associativity of ⊕"),
    "id_add": ("a ⊕ 0", "a", "Identity element of ⊕"),
    "inv_add": ("a ⊕ (⊖a)", "0", "Inverse under ⊕"),

    "comm_mul": ("a ⊗ b", "b ⊗ a", "Commutativity of ⊗"),
    "assoc_mul": ("(a ⊗ b) ⊗ c", "a ⊗ (b ⊗ c)", "Associativity of ⊗"),
    "id_mul": ("a ⊗ 1", "a", "Identity element of ⊗"),
    "inv_mul": ("a ⊗ (/a)", "1", "Inverse under ⊗"),

    # Equivalence & Entanglement
    "sym_eq": ("a ↔ b", "b ↔ a", "Symmetry of entanglement ↔"),
    "ref_eq": ("a ↔ a", "✦", "Reflexivity of entanglement (milestone)"),

    # Gradient / Entropy Rules (use Grad() structurally)
    "grad_zero": ("∇(0)", "0", "Gradient of zero is zero"),
    "grad_const": ("∇(c)", "0", "Gradient of constant is zero"),
    "grad_add": ("∇(a ⊕ b)", "∇(a) ⊕ ∇(b)", "Gradient distributes over ⊕"),
    "grad_mul": ("∇(a ⊗ b)", "(∇(a) ⊗ b) ⊕ (a ⊗ ∇(b))", "Product rule for ∇"),

    # Collapse / Mutation
    "collapse_id": ("⟲a", "a", "Mutation collapse identity"),
}


# -------------------------------------------------------------------
# Export Helpers
# -------------------------------------------------------------------

def list_axioms() -> Dict[str, Tuple[str, str, str]]:
    """Return all Photon axioms as a dict."""
    return AXIOMS


def axioms_sympy() -> Dict[str, Tuple[str, str, str]]:
    """Return axioms with glyphs converted to Sympy-safe syntax."""
    converted = {}
    for name, (lhs, rhs, desc) in AXIOMS.items():
        lhs_conv = _glyph_to_sympy(lhs)
        rhs_conv = _glyph_to_sympy(rhs)
        converted[name] = (lhs_conv, rhs_conv, desc)
    return converted


def axioms_to_markdown() -> str:
    """Format Photon axioms as a Markdown table (glyph form)."""
    header = "| Axiom | Pattern | Replacement | Description |\n"
    header += "|-------|---------|-------------|-------------|\n"
    rows = []
    for name, (lhs, rhs, desc) in AXIOMS.items():
        rows.append(f"| {name} | `{lhs}` | `{rhs}` | {desc} |")
    return header + "\n".join(rows)


def axioms_to_markdown_sympy() -> str:
    """Format Photon axioms into Sympy-safe Markdown table."""
    header = "| Axiom | LHS (Sympy) | RHS (Sympy) | Description |\n"
    header += "|-------|-------------|-------------|-------------|\n"
    rows = []
    for name, (lhs, rhs, desc) in AXIOMS.items():
        lhs_sym = _glyph_to_sympy(lhs)
        rhs_sym = _glyph_to_sympy(rhs)
        rows.append(f"| {name} | `{lhs_sym}` | `{rhs_sym}` | {desc} |")
    return header + "\n".join(rows)


# -------------------------------------------------------------------
# Debug / Preview Mode
# -------------------------------------------------------------------

if __name__ == "__main__":
    print("Photon Axioms (glyphs):")
    for k, (lhs, rhs, desc) in AXIOMS.items():
        print(f" - {k}: {lhs} -> {rhs}  # {desc}")

    print("\nPhoton Axioms (Sympy-safe):")
    for k, (lhs, rhs, desc) in axioms_sympy().items():
        print(f" - {k}: {lhs} -> {rhs}  # {desc}")

    print("\nMarkdown Export (glyphs):\n")
    print(axioms_to_markdown())

    print("\nMarkdown Export (Sympy-safe):\n")
    print(axioms_to_markdown_sympy())