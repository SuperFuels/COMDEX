# backend/photon_algebra/photon_pp.py
"""
Photon Algebra Pretty-Printer
-----------------------------
Pretty-printer for Photon ASTs, using Unicode infix symbols
with minimal parentheses (based on operator precedence) and
a few targeted rules to preserve intended grouping:

- Always parenthesize composite children under ↔
  (e.g., a ↔ (b ⊕ c)), to match regression expectations.
- For ⊗ (and ⊖), parenthesize same-op children to preserve
  association (e.g., a ⊗ (a ⊗ b)), avoiding parse re-association.
"""

from typing import Any

# Operator precedences (higher binds tighter)
_PRECEDENCE = {
    "¬": 4,
    "★": 4,
    "⊗": 3,
    "⊖": 2,
    "⊕": 2,
    "↔": 1,  # lowest precedence
}

_INFIX_OPS = {"⊕", "⊗", "⊖", "↔"}


def _needs_parens(parent_op: str, child: Any) -> bool:
    """Decide if child should be parenthesized under parent_op."""
    if not isinstance(child, dict):
        return False

    cop = child.get("op")

    # Special: Under ↔, parenthesize any composite child to match expected strings
    if parent_op == "↔" and cop in _INFIX_OPS:
        return True

    # Preserve tree for association-sensitive ops:
    # If child uses the same op as the parent for ⊗ or ⊖, add parens to keep grouping.
    if parent_op in ("⊗", "⊖") and cop == parent_op:
        return True

    # Standard precedence-based parentheses:
    # If child's precedence is LOWER than parent's, we need parentheses.
    if _PRECEDENCE.get(cop, 0) < _PRECEDENCE.get(parent_op, 0):
        return True

    return False


def _pp(expr: Any, parent_prec: int = 0) -> str:
    """Recursive pretty-printer with operator precedence awareness."""
    if not isinstance(expr, dict):
        return str(expr)

    op = expr.get("op")

    # Constants
    if op == "∅":
        return "∅"

    # Unary ops
    if op in ("¬", "★"):
        inner = _pp(expr.get("state"), _PRECEDENCE[op])
        s = f"{op}{inner}"
        # If parent is tighter, wrap this unary
        if _PRECEDENCE[op] < parent_prec:
            return f"({s})"
        return s

    # Infix / n-ary ops
    if op in _INFIX_OPS:
        parts = []
        for ch in expr.get("states", []):
            rendered = _pp(ch, _PRECEDENCE[op])
            if _needs_parens(op, ch):
                # Ensure single set of parens; don't double-wrap
                if not (rendered.startswith("(") and rendered.endswith(")")):
                    rendered = f"({rendered})"
            parts.append(rendered)

        s = f" {op} ".join(parts)
        # Parenthesize the whole expression if our op is looser than the parent
        if _PRECEDENCE[op] < parent_prec:
            return f"({s})"
        return s

    # Fallback generic (functional style, still respects precedence)
    if "states" in expr:
        return f"{op}(" + ", ".join(_pp(s, _PRECEDENCE.get(op, 0)) for s in expr["states"]) + ")"
    if "state" in expr:
        return f"{op}(" + _pp(expr["state"], _PRECEDENCE.get(op, 0)) + ")"
    return str(expr)


def pp(expr: Any) -> str:
    """Pretty-print expression (safe for round-tripping)."""
    return _pp(expr, 0)


def pretty(expr: Any) -> str:
    """Alias for external callers."""
    return pp(expr)


if __name__ == "__main__":
    # Debug harness
    demo1 = {"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]}
    demo2 = {"op": "⊕", "states": [{"op": "↔", "states": ["a", "b"]}, "c"]}
    demo3 = {"op": "↔", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]}
    demo4 = {"op": "⊗", "states": ["a", {"op": "⊗", "states": ["a", "b"]}]}

    print("Expr 1:", demo1, "→", pp(demo1))  # a ⊗ (b ⊕ c)
    print("Expr 2:", demo2, "→", pp(demo2))  # (a ↔ b) ⊕ c
    print("Expr 3:", demo3, "→", pp(demo3))  # a ↔ (b ⊕ c)
    print("Expr 4:", demo4, "→", pp(demo4))  # a ⊗ (a ⊗ b)