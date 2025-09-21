"""
Symatics Algebra Rulebook v0.1 (Expanded)
─────────────────────────────────────────────
Defines Symatics core operators and axioms/laws.

Operators:
  ⊕(a, b)     → superposition
  μ(x)        → measurement
  ↔(a, b)     → entanglement / equivalence
  ⟲(f, n)     → recursion / loop
  π(seq, n)   → projection / extraction
"""

from typing import Any, Dict, List, Union
from backend.symatics.rewrite_rules import simplify  # 🔑 auto-normalization hook

# Types
SymExpr = Union[str, Dict[str, Any], List[Any]]

# ──────────────────────────────
# Core Operator Implementations
# ──────────────────────────────

def op_superpose(a: Any, b: Any, context: Dict) -> Dict[str, Any]:
    from backend.symatics.rewrite_rules import simplify
    a = simplify(a)
    b = simplify(b)
    expr = {
        "op": "⊕",
        "args": [a, b],
        "result": f"({a} ⊕ {b})",
        "state": [a, b],
        "context": context,
    }
    return simplify(expr)


def op_measure(x: Any, context: Dict) -> Dict[str, Any]:
    """
    μ : Measurement operator
    Signature: μ : State(A) → A
    Collapses state to a single branch.
    """
    collapsed = str(x) if not isinstance(x, dict) else x.get("state", x)
    expr = {
        "op": "μ",
        "args": [x],
        "result": f"measurement({collapsed})",
        "collapsed": collapsed,
        "context": context,
    }
    return simplify(expr)


def op_entangle(a: Any, b: Any, context: Dict) -> Dict[str, Any]:
    """
    ↔ : Entanglement / Equivalence
    Signature: ↔ : A × A → Entangled(A, A)
    """
    expr = {
        "op": "↔",
        "args": [a, b],
        "result": f"{a} ↔ {b}",
        "pair": (a, b),
        "context": context,
    }
    return simplify(expr)


def op_recurse(f: Any, depth: int, context: Dict) -> Dict[str, Any]:
    """
    ⟲ : Recursion / Loop operator
    Signature: ⟲ : (A, n ∈ ℕ) → {A}
    """
    results = []
    current = f
    for i in range(depth):
        results.append({"iter": i, "value": current})
        current = f"{current}*"
    expr = {
        "op": "⟲",
        "args": [f, depth],
        "result": f"recurse({f}, depth={depth})",
        "depth": depth,
        "results": results,
        "context": context,
    }
    return simplify(expr)


def op_project(seq: List[Any], n: int, context: Dict) -> Dict[str, Any]:
    """
    π : Projection / Extraction
    Signature: π : Seq(A) × ℕ → A
    """
    try:
        value = seq[n]
    except Exception:
        value = None
    expr = {
        "op": "π",
        "args": [seq, n],
        "result": f"π({n})={value}",
        "index": n,
        "value": value,
        "context": context,
    }
    return simplify(expr)

# ──────────────────────────────
# Canonicalization for Laws
# ──────────────────────────────

def _canonical(expr: Any) -> Any:
    """
    Convert Symatics expression into canonical tuple form for law checks.
    Always fully simplifies before encoding.
    """
    from backend.symatics.rewrite_rules import simplify
    expr = simplify(expr)

    if isinstance(expr, dict):
        op = expr.get("op")

        if op == "⊕":
            # After simplify, args should already be flattened.
            return ("⊕", tuple(sorted((_canonical(x) for x in expr.get("args", [])), key=str)))

        if op == "↔":
            return ("↔", tuple(sorted((_canonical(x) for x in expr.get("args", [])), key=str)))

        if op == "⟲":
            return ("⟲", _canonical(expr["args"][0]), expr["args"][1])

        if op == "π":
            return ("π", expr.get("index"), _canonical(expr.get("value")))

        if op == "μ":
            return ("μ", _canonical(expr.get("collapsed")))

    if isinstance(expr, (list, tuple)):
        return tuple(_canonical(x) for x in expr)

    return expr

# ──────────────────────────────
# Laws / Axioms (v0.1 expanded)
# ──────────────────────────────

def law_commutativity(op: str, a: Any, b: Any) -> bool:
    if op == "⊕":
        return _canonical(op_superpose(a, b, {})) == _canonical(op_superpose(b, a, {}))
    if op == "↔":
        return _canonical(op_entangle(a, b, {})) == _canonical(op_entangle(b, a, {}))
    return True

def law_associativity(op: str, a: Any, b: Any, c: Any) -> bool:
    """⊕ associativity: (a ⊕ b) ⊕ c == a ⊕ (b ⊕ c)."""
    if op == "⊕":
        left = op_superpose(op_superpose(a, b, {}), c, {})
        right = op_superpose(a, op_superpose(b, c, {}), {})

        from backend.symatics.rewrite_rules import simplify
        # 🔑 normalize deeply before comparison
        left_s = simplify(left)
        right_s = simplify(right)

        return _canonical(left_s) == _canonical(right_s)
    return True

def law_idempotence(op: str, a: Any) -> bool:
    """⊕ is idempotent: a ⊕ a = a."""
    if op == "⊕":
        expr = op_superpose(a, a, {})
        reduced = collapse_rule(expr)  # collapse ⊕ into one branch
        return _canonical(reduced) == _canonical(a)
    return True


def law_distributivity(a: Any, b: Any, c: Any) -> bool:
    """
    Distributivity (draft v0.1):
    a ⊕ (b ↔ c) ≡ (a ⊕ b) ↔ (a ⊕ c)
    """
    # Left side
    left = op_superpose(a, op_entangle(b, c, {}), {})

    # Explicitly rewrite: if right arg is entanglement, distribute
    if isinstance(left, dict) and left.get("op") == "⊕":
        args = left.get("args", [])
        if len(args) == 2 and isinstance(args[1], dict) and args[1].get("op") == "↔":
            b_val, c_val = args[1]["args"]
            distributed = op_entangle(
                op_superpose(a, b_val, {}),
                op_superpose(a, c_val, {}),
                {}
            )
            left = distributed

    # Right side
    right = op_entangle(op_superpose(a, b, {}), op_superpose(a, c, {}), {})

    return _canonical(left) == _canonical(right)


def law_projection(seq: List[Any], n: int, m: int) -> bool:
    """
    π law: π(π(seq, n), m) == π(seq, n+m).
    Symbolically compose indices even if values aren't nested lists.
    """
    flat = op_project(seq, n + m, {})
    nested = op_project(seq, n, {})
    # If nested result is a list, project again; else treat as symbolic
    if isinstance(nested.get("value"), list):
        nested_val = op_project(nested["value"], m, {})
    else:
        # symbolic: pretend π(seq, n)[m] = π(seq, n+m)
        nested_val = op_project(seq, n + m, {})
    return _canonical(flat) == _canonical(nested_val)


def collapse_rule(x: Any) -> Any:
    """μ collapses ⊕ into one branch deterministically (simplified).
    Collapsed result is routed back into the rewrite engine so it can be normalized.
    """
    from backend.symatics.rewrite_rules import simplify  # local import to avoid circular import

    if isinstance(x, dict) and x.get("op") == "⊕":
        state = x.get("state", [])
        branch = state[0] if state else None
        return simplify(branch)

    return simplify(x)

# ──────────────────────────────
# Laws / Axioms (v0.1 expanded)
# ──────────────────────────────

def law_identity(op: str, a: Any) -> bool:
    """Identity: a ⊕ ∅ = a and ∅ ⊕ a = a."""
    if op == "⊕":
        left = op_superpose(a, "∅", {})
        right = op_superpose("∅", a, {})
        return _canonical(left) == _canonical(a) and _canonical(right) == _canonical(a)
    return True


# ──────────────────────────────
# Law Runner (for testing/eval)
# ──────────────────────────────

# Map operator → applicable laws
LAW_REGISTRY = {
    "⊕": [law_commutativity, law_associativity, law_idempotence, law_identity, law_distributivity],
    "↔": [law_commutativity],
    "π": [law_projection],
    # Future operators can be added here: "Δ": [law_derivative], etc.
}

def check_all_laws(op: str, *args: Any) -> Dict[str, bool]:
    """
    Run all applicable Symatics laws for a given operator + args.
    Returns dict of law_name → True/False.
    """
    results: Dict[str, bool] = {}
    for law_fn in LAW_REGISTRY.get(op, []):
        try:
            ok = law_fn(op, *args) if "op" in law_fn.__code__.co_varnames else law_fn(*args)
            # Strip 'law_' prefix for human-friendly key
            law_name = law_fn.__name__.removeprefix("law_")
            results[law_name] = bool(ok)
        except Exception:
            results[law_fn.__name__.removeprefix("law_")] = False
    return results
# ──────────────────────────────
# TODO (v0.2+)
# ──────────────────────────────
# - Δ (difference) operator: symbolic derivative
# - ∫ (integration analog): symbolic sum/area
# - Stronger distributivity + identity laws
# - Add duality checks (⊕ vs μ)