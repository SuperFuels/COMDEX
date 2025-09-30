# backend/photon_algebra/rewriter.py

import copy
from typing import Any, Dict, List, Tuple, Union

from .core import EMPTY  # 🔑 shared canonical empty state

Expr = Union[str, Dict[str, Any]]

# -------------------------------------------
# Pattern Matching
# -------------------------------------------

def match(expr: Expr, pattern: Expr, env=None):
    """
    Match expr against a pattern with wildcards.
    Wildcards = strings starting with lowercase (e.g., "a", "b").
    Returns mapping {var: subexpr} or None if no match.
    """
    if env is None:
        env = {}

    # Variable placeholder
    if isinstance(pattern, str) and pattern.islower():
        if pattern in env and env[pattern] != expr:
            return None
        env[pattern] = expr
        return env

    # Exact match
    if isinstance(pattern, str):
        return env if expr == pattern else None

    # Dict patterns
    if isinstance(pattern, dict) and isinstance(expr, dict):
        if pattern.get("op") != expr.get("op"):
            return None
        if "states" in pattern:
            if len(pattern["states"]) != len(expr.get("states", [])):
                return None
            for p, e in zip(pattern["states"], expr["states"]):
                env = match(e, p, env)
                if env is None:
                    return None
        if "state" in pattern:
            env = match(expr.get("state"), pattern["state"], env)
        return env

    return None


def substitute(pattern: Expr, env: Dict[str, Expr]) -> Expr:
    """Substitute wildcards in a pattern with values from env."""
    if isinstance(pattern, str) and pattern.islower():
        return env.get(pattern, pattern)
    if isinstance(pattern, str):
        return pattern
    if isinstance(pattern, dict):
        new_expr = {"op": pattern["op"]}
        if "states" in pattern:
            new_expr["states"] = [substitute(s, env) for s in pattern["states"]]
        if "state" in pattern:
            new_expr["state"] = substitute(pattern["state"], env)
        return new_expr
    return copy.deepcopy(pattern)


# -------------------------------------------
# Rewrite Rules (axioms + theorems)
# -------------------------------------------

REWRITE_RULES: List[Tuple[Expr, Expr]] = [
    # Associativity: (a ⊕ b) ⊕ c → a ⊕ (b ⊕ c)
    (
        {"op": "⊕", "states": [{"op": "⊕", "states": ["a", "b"]}, "c"]},
        {"op": "⊕", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
    ),
    # Commutativity: a ⊕ b → b ⊕ a
    (
        {"op": "⊕", "states": ["a", "b"]},
        {"op": "⊕", "states": ["b", "a"]},
    ),
    # Idempotence: a ⊕ a → a
    (
        {"op": "⊕", "states": ["a", "a"]},
        "a",
    ),
    # Distributivity: a ⊗ (b ⊕ c) → (a ⊗ b) ⊕ (a ⊗ c)
    (
        {"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
        {"op": "⊕", "states": [
            {"op": "⊗", "states": ["a", "b"]},
            {"op": "⊗", "states": ["a", "c"]},
        ]},
    ),
    # Cancellation: a ⊖ a → ∅
    (
        {"op": "⊖", "states": ["a", "a"]},
        EMPTY,
    ),
    # Double Negation: ¬(¬a) → a
    (
        {"op": "¬", "state": {"op": "¬", "state": "a"}},
        "a",
    ),
    # T10 — Entanglement distributivity:
    # (a↔b) ⊕ (a↔c) → a↔(b⊕c)
    (
        {"op": "⊕", "states": [
            {"op": "↔", "states": ["a", "b"]},
            {"op": "↔", "states": ["a", "c"]},
        ]},
        {"op": "↔", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
    ),
    # T12 — Projection fidelity:
    # ★(a↔b) → (★a) ⊕ (★b)
    (
        {"op": "★", "state": {"op": "↔", "states": ["a", "b"]}},
        {"op": "⊕", "states": [
            {"op": "★", "state": "a"},
            {"op": "★", "state": "b"},
        ]},
    ),
    # T13 — Absorption:
    # a ⊕ (a ⊗ b) → a
    (
        {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["a", "b"]}]},
        "a",
    ),
    (
        {"op": "⊕", "states": [{"op": "⊗", "states": ["a", "b"]}, "a"]},
        "a",
    ),
    # T14 — Dual Distributivity:
    # a ⊕ (b ⊗ c) → (a ⊕ b) ⊗ (a ⊕ c)
    (
        {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["b", "c"]}]},
        {"op": "⊗", "states": [
            {"op": "⊕", "states": ["a", "b"]},
            {"op": "⊕", "states": ["a", "c"]},
        ]},
    ),
    # T15 — Falsification:
    # a ⊖ ∅ → a
    (
        {"op": "⊖", "states": ["a", {"op": "∅"}]},
        "a",
    ),
    (
        {"op": "⊖", "states": [{"op": "∅"}, "a"]},
        "a",
    ),
]


# -------------------------------------------
# Rewriter Engine
# -------------------------------------------

def apply_rules(expr: Expr) -> Expr:
    """Try applying one rewrite rule to expr, return new expr or same if no match."""
    for pattern, replacement in REWRITE_RULES:
        env = match(expr, pattern)
        if env is not None:
            return substitute(replacement, env)
    # Recurse
    if isinstance(expr, dict):
        if "states" in expr:
            expr = {**expr, "states": [apply_rules(s) for s in expr["states"]]}
        if "state" in expr:
            expr = {**expr, "state": apply_rules(expr["state"])}
    return expr


def normalize(expr: Any) -> Any:
    """
    Normalize Photon Algebra expressions under axioms + theorems:
    - Associativity, Commutativity, Idempotence
    - Distributivity (⊗ over ⊕, ↔ over ⊕)
    - Cancellation: a ⊖ a = ∅
    - Double Negation: ¬(¬a) = a
    - Projection Fidelity: ★(a↔b) → ★a ⊕ ★b
    - Collapse Consistency: remove ∅ from superpositions
    """
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")
    states = expr.get("states", [])

    # Normalize children first
    norm_states = [normalize(s) for s in states]

    if op == "⊕":
        # Flatten nested ⊕
        flat = []
        for s in norm_states:
            if isinstance(s, dict) and s.get("op") == "⊕":
                flat.extend(s["states"])
            else:
                flat.append(s)

        # Remove ∅ (T11 support)
        flat = [s for s in flat if s != EMPTY]

        # Deduplicate
        flat_unique = []
        for s in flat:
            if s not in flat_unique:
                flat_unique.append(s)

        # Commutativity: sort (stringify for stability)
        flat_sorted = sorted(flat_unique, key=lambda x: str(x))

        if not flat_sorted:
            return EMPTY
        if len(flat_sorted) == 1:
            return flat_sorted[0]
        return {"op": "⊕", "states": flat_sorted}

    elif op == "⊗":
        if len(norm_states) == 2:
            a, b = norm_states
            # Distributivity: ⊗ over ⊕
            if isinstance(b, dict) and b.get("op") == "⊕":
                return normalize({
                    "op": "⊕",
                    "states": [{"op": "⊗", "states": [a, bi]} for bi in b["states"]]
                })
            if isinstance(a, dict) and a.get("op") == "⊕":
                return normalize({
                    "op": "⊕",
                    "states": [{"op": "⊗", "states": [ai, b]} for ai in a["states"]]
                })
        return {"op": "⊗", "states": norm_states}

    elif op == "↔":
        if len(norm_states) == 2:
            a, b = norm_states
            # Entanglement distributivity: (a↔b) ⊕ (a↔c)
            if isinstance(b, dict) and b.get("op") == "⊕":
                return normalize({
                    "op": "⊕",
                    "states": [{"op": "↔", "states": [a, bi]} for bi in b["states"]]
                })
        return {"op": "↔", "states": norm_states}

    elif op == "⊖":  # Cancellation
        if len(norm_states) == 2 and norm_states[0] == norm_states[1]:
            return EMPTY
        return {"op": "⊖", "states": norm_states}

    elif op == "¬":  # Negation
        inner = expr.get("state") or (expr.get("states") or [None])[0]
        inner_norm = normalize(inner)
        if isinstance(inner_norm, dict) and inner_norm.get("op") == "¬":
            return normalize(inner_norm.get("state") or (inner_norm.get("states") or [None])[0])
        return {"op": "¬", "state": inner_norm}

    elif op == "★":  # Projection
        inner = expr.get("state")
        inner_norm = normalize(inner)
        if isinstance(inner_norm, dict) and inner_norm.get("op") == "↔":
            a, b = inner_norm.get("states", [None, None])
            return normalize({"op": "⊕", "states": [
                {"op": "★", "state": a},
                {"op": "★", "state": b},
            ]})
        return {"op": "★", "state": inner_norm}

    elif op == "∅":
        return EMPTY

    else:
        return {"op": op, "states": norm_states}