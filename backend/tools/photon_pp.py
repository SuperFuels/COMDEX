from __future__ import annotations
from typing import Any

# Operator precedences (lower number = weaker binding)
_PRECEDENCE = {
    "↔": 1,   # weakest
    "≈": 1,   # treat like entanglement (weak)
    "⊂": 1,   # treat like entanglement (weak)
    "⊕": 2,
    "⊖": 2,   # same as ⊕, but non-commutative
    "⊗": 3,
    "¬": 4,
    "★": 4,
    "∅": 5,
    "⊤": 5,   # constants
    "⊥": 5,
    None: 99,  # atoms
}


def _needs_parens(parent_op: str, child: Any, side: str | None = None) -> bool:
    """Decide if child expression needs parentheses under parent_op."""
    if not isinstance(child, dict):
        return False

    cop = child.get("op")

    # For entanglement-like weak ops (↔, ≈, ⊂):
    if parent_op in ("↔", "≈", "⊂"):
        # If child is also one of these, parenthesize to preserve grouping
        if cop in ("↔", "≈", "⊂"):
            return True
        # If child is a stronger op, parenthesize
        if cop in ("⊕", "⊖", "⊗"):
            return True

    # Cancellation (⊖): force parentheses if child is also ⊕/⊖ to disambiguate
    if parent_op == "⊖" and cop in ("⊕", "⊖"):
        return True

    # Superposition (⊕): if child is ⊖, wrap
    if parent_op == "⊕" and cop == "⊖":
        return True

    # Fusion (⊗): parenthesize right-hand child if also ⊗ (left-associative)
    if parent_op == "⊗" and cop == "⊗" and side == "right":
        return True

    return False


def _pp(expr: Any, parent_op: str | None = None, side: str | None = None) -> str:
    if not isinstance(expr, dict):
        return str(expr)

    op = expr.get("op")

    # Unary operators
    if op == "¬":
        inner = _pp(expr["state"], "¬")
        return f"¬{inner}"
    if op == "★":
        inner = _pp(expr["state"], "★")
        return f"★{inner}"
    if op in ("∅", "⊤", "⊥"):
        return op

    states = expr.get("states", [])

    if op in ("⊕", "⊗", "↔", "≈", "⊂"):
        parts = []
        for i, s in enumerate(states):
            side_tag = "left" if i == 0 else "right"
            sub = _pp(s, op, side=side_tag)
            if _needs_parens(op, s, side=side_tag):
                sub = f"({sub})"
            parts.append(sub)
        s = f" {op} ".join(parts)

    elif op == "⊖":
        if len(states) != 2:
            parts = []
            for i, s in enumerate(states):
                side_tag = "left" if i == 0 else "right"
                sub = _pp(s, op, side=side_tag)
                if _needs_parens(op, s, side=side_tag):
                    sub = f"({sub})"
                parts.append(sub)
            s = f" {op} ".join(parts)
        else:
            left, right = states
            left_s = _pp(left, op, side="left")
            right_s = _pp(right, op, side="right")

            if _needs_parens("⊖", left, "left"):
                left_s = f"({left_s})"
            if _needs_parens("⊖", right, "right"):
                right_s = f"({right_s})"

            s = f"{left_s} ⊖ {right_s}"

    else:
        # Unknown dict fallback
        return str(expr)

    # Parentheses if outer precedence is weaker
    if parent_op is not None and _PRECEDENCE[op] < _PRECEDENCE[parent_op]:
        s = f"({s})"
    return s


def pp(expr: Any) -> str:
    """Pretty-print AST into a string."""
    return _pp(expr)
