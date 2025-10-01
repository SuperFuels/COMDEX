# -*- coding: utf-8 -*-
"""
Executable Doc Tests — Photon Normalization Spec
------------------------------------------------
Parses `docs/rfc/photon_normalization.md` and checks that all
example reductions actually hold under normalize().
"""

import re
import pathlib
import pytest
import json
from backend.photon_algebra import rewriter

# Path to the spec
DOC_PATH = pathlib.Path("docs/rfc/photon_normalization.md")

# Pattern: `lhs → rhs`
EXAMPLE_PATTERN = re.compile(r"^-\s*`(.+?)`\s*→\s*`(.+?)`", re.UNICODE)


def parse_examples():
    """Extract example reductions from the RFC markdown."""
    text = DOC_PATH.read_text(encoding="utf-8")
    examples = []
    for line in text.splitlines():
        m = EXAMPLE_PATTERN.match(line.strip())
        if m:
            lhs, rhs = m.groups()
            examples.append((lhs, rhs))
    return examples


@pytest.mark.parametrize("lhs,rhs", parse_examples())
def test_doc_examples(lhs, rhs):
    """Ensure all RFC example reductions hold under normalize()."""
    lhs_norm = rewriter.normalize(_parse_expr(lhs))
    rhs_norm = rewriter.normalize(_parse_expr(rhs))

    if lhs_norm != rhs_norm:
        lhs_str = json.dumps(lhs_norm, indent=2, ensure_ascii=False)
        rhs_str = json.dumps(rhs_norm, indent=2, ensure_ascii=False)
        raise AssertionError(
            f"Failed reduction: {lhs} → {rhs}\n\n"
            f"LHS normalized:\n{lhs_str}\n\n"
            f"RHS normalized:\n{rhs_str}\n"
        )


# --- Minimal parser ---------------------------------------------------------
def _parse_expr(s: str):
    """
    Recursive parser for doc examples into Photon AST.
    Supports:
      - Atoms: a, b, c
      - Empty: ∅
      - Unary: ¬(x)
      - Binary: (a ⊕ b), (a ⊗ b), (a ⊖ b), (a ↔ b)
      - Nested parens
    """
    s = s.strip()
    if s == "∅":
        return {"op": "∅"}
    if len(s) == 1 and s.isalpha():
        return s

    # Strip outer parens
    if s.startswith("(") and s.endswith(")"):
        # ensure matching parens
        depth = 0
        match = True
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if depth == 0 and i < len(s) - 1:
                match = False
                break
        if match:
            s = s[1:-1].strip()

    # Unary ¬
    if s.startswith("¬"):
        inner = s[1:].strip()
        if inner.startswith("(") and inner.endswith(")"):
            inner = inner[1:-1].strip()
        return {"op": "¬", "state": _parse_expr(inner)}

    # Binary ops with paren-aware splitting
    for op in ["⊕", "⊗", "⊖", "↔"]:
        parts = _split_top_level(s, op)
        if parts:
            return {"op": op, "states": [_parse_expr(parts[0]), _parse_expr(parts[1])]}

    return s


def _split_top_level(s: str, op: str):
    """Split string by `op` at top level (ignores parens)."""
    depth = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and s.startswith(op, i):
            return s[:i].strip(), s[i+len(op):].strip()
    return None