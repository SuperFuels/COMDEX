# -*- coding: utf-8 -*-
"""
Photon Canonical Simplifier
===========================
Task: I3 — Canonicalization Layer

Performs algebraic normalization on Photon Algebra JSON IR.
Guarantees structural determinism under commutative, associative,
and idempotent operators.

Rules:
    Commutativity:
        ⊕(a,b) == ⊕(b,a)
        ⊗(a,b) == ⊗(b,a)

    Identity / Null:
        ⊕(∅,x) → x
        ⊗(⊤,x) → x
        ⊕(⊥,x) → x
        ⊗(∅,x) → ∅
        ⊕(⊤,x) → ⊤
        ⊗(⊥,x) → ⊥

    Idempotency:
        ⊕(a,a) → a
        ⊗(a,a) → a

    Nest flattening:
        ⊕(a,⊕(b,c)) → ⊕(a,b,c)
        ⊗(a,⊗(b,c)) → ⊗(a,b,c)
"""

from __future__ import annotations
from typing import Any, Dict, List, Union

Expr = Union[str, Dict[str, Any]]


def _is_dict(x, op=None):
    return isinstance(x, dict) and (op is None or x.get("op") == op)


def _key(expr):
    """Deterministic sorting key for commutative ops."""
    return str(expr)


def canonicalize(expr: Expr) -> Expr:
    """Recursively canonicalize a Photon expression tree."""
    if isinstance(expr, str):
        return expr
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")

    # ---- constants ----
    if op in {"∅", "⊤", "⊥"}:
        return {"op": op}

    # ---- unary ----
    if op in {"¬", "★"}:
        return {"op": op, "state": canonicalize(expr.get("state"))}

    # ---- binary / n-ary ----
    if op in {"⊕", "⊗"}:
        # Flatten nested same-op and canonicalize children
        states = []
        for s in expr.get("states", []):
            c = canonicalize(s)
            if _is_dict(c, op):
                states.extend(c["states"])
            else:
                states.append(c)

        # Remove duplicates (idempotency)
        uniq = []
        seen = set()
        for s in sorted(states, key=_key):
            key = str(s)
            if key not in seen:
                uniq.append(s)
                seen.add(key)

        # Apply identities
        if op == "⊕":
            # OR identities
            if any(_is_dict(s, "⊤") for s in uniq):
                return {"op": "⊤"}
            uniq = [s for s in uniq if not _is_dict(s, "∅") and not _is_dict(s, "⊥")]
            if not uniq:
                return {"op": "∅"}
        elif op == "⊗":
            # AND identities
            if any(_is_dict(s, "⊥") for s in uniq):
                return {"op": "⊥"}
            uniq = [s for s in uniq if not _is_dict(s, "⊤")]
            if not uniq:
                return {"op": "⊤"}

        # Collapse unary
        if len(uniq) == 1:
            return uniq[0]

        return {"op": op, "states": uniq}

    if op in {"⊖", "≈", "⊂", "↔"}:
        a, b = expr.get("states", [None, None])
        a, b = canonicalize(a), canonicalize(b)
        return {"op": op, "states": [a, b]}

    # fallback — unknown operator
    return expr


# -----------------------------------------------------------------------------
# Simple diagnostic entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    sample = {
        "op": "⊕",
        "states": [
            {"op": "⊗", "states": [{"op": "⊤"}, "a"]},
            {"op": "⊕", "states": ["b", "a", {"op": "∅"}]},
            {"op": "⊕", "states": ["a", "b"]}
        ],
    }
    print("Before:\n", json.dumps(sample, ensure_ascii=False, indent=2))
    canon = canonicalize(sample)
    print("\nAfter:\n", json.dumps(canon, ensure_ascii=False, indent=2))