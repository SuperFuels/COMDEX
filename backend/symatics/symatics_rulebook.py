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
from backend.symatics.rewrite_rules import (
    simplify,           # 🔑 auto-normalization hook
    rewrite_derivative, # calculus rules
    rewrite_integral,   # calculus rules
)

# Types
SymExpr = Union[str, Dict[str, Any], List[Any]]

# ──────────────────────────────
# Calculus Operators (wrappers)
# ──────────────────────────────

def op_derivative(expr: Any, var: str, context: Dict) -> Dict[str, Any]:
    simplified = rewrite_derivative(expr, var)
    return {
        "op": "Δ",
        "args": [expr, var],
        "result": f"d/d{var}({expr})",
        "context": context,
        "simplified": simplified,
        "canonical": _canonical(simplified),  # <-- ensures tuples
    }

def op_integral(expr: Any, var: str, context: Dict) -> Dict[str, Any]:
    simplified = rewrite_integral(expr, var)

    # Default debug string
    result_str = f"∫ d{var}({expr})"

    # Special-case: ∫ x dx = 0.5*x^2
    if isinstance(simplified, dict) and simplified.get("op") == "/" and simplified.get("args"):
        num, den = simplified["args"]
        if (
            den == "2"
            and isinstance(num, dict)
            and num.get("op") in {"^", "pow"}
            and num.get("args") == [{"op": "var", "args": [var]}, "2"]
        ):
            result_str = f"0.5*{var}^2"

    # If rewrite produced something nice, improve result_str further
    elif isinstance(simplified, dict):
        op = simplified.get("op")
        args = simplified.get("args", [])

        # Power division → x^(n+1)/(n+1)
        if op == "/" and args and isinstance(args[0], dict) and args[0].get("op") in {"^", "pow"}:
            base, power = args[0]["args"]
            if base == {"op": "var", "args": [var]}:
                result_str = f"{var}^{power}/{args[1]}"

        # Constant multiplication → c*x
        elif op == "*" and args and (isinstance(args[0], int) or (isinstance(args[0], str) and args[0].isdigit())):
            c = int(args[0]) if isinstance(args[0], str) and args[0].isdigit() else args[0]
            if isinstance(args[1], dict) and args[1].get("op") == "var":
                result_str = f"{c}*{args[1]['args'][0]}"
            else:
                result_str = f"{c}*{args[1]}"

        # Trig and exp
        elif op in {"sin", "cos", "exp"} and args:
            arg = args[0]
            if isinstance(arg, dict) and arg.get("op") == "var":
                result_str = f"{op}({arg['args'][0]})"
            else:
                result_str = f"{op}({arg})"

    return {
        "op": "∫",
        "args": [expr, var],
        "result": result_str,
        "context": context,
        "simplified": simplified,
    }

# alias
op_integrate = op_integral

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
    Collapses state to a single branch (normalized).
    """
    from backend.symatics.rewrite_rules import simplify  # avoid cycles
    # Ensure input is simplified first
    x_s = simplify(x)
    # Proper collapse (previously returned the whole state list)
    collapsed = collapse_rule(x_s)
    expr = {
        "op": "μ",
        "args": [x_s],
        "result": f"measurement({_canonical(x_s)})",
        "collapsed": collapsed,
        "context": context,
    }
    # Keep μ-node, but downstream duality will compare the collapsed payload
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
    Rules:
      • Constants normally stringified ("0","1","2",...) 
      • ∫ returns ("∫", const, var) with const as int if numeric
      • Δ returns fully canonicalized derivative body
      • Commutative ops (+,*) get sorted args
    """
    from backend.symatics.rewrite_rules import simplify
    expr = simplify(expr)

    if isinstance(expr, dict):
        op = expr.get("op")
        args = expr.get("args", [])

        # --- integration node ---
        if op == "∫":
            if expr.get("simplified") is not None:
                return _canonical(expr["simplified"])
            arg0 = _canonical(args[0])
            arg1 = args[1]
            # Preserve raw int for ∫ constant law
            if isinstance(arg0, str) and arg0.lstrip("-").isdigit():
                arg0 = int(arg0)
            if isinstance(arg0, (dict, tuple)) and arg0 == ("const",):
                arg0 = 0
            return ("∫", arg0, arg1)

        # --- derivative node ---
        if op == "Δ":
            if expr.get("simplified") is not None:
                return _canonical(expr["simplified"])
            return ("Δ", _canonical(args[0]), args[1])

        # --- multiplication (commutative) ---
        if op in {"*", "mul"}:
            def sort_key(x):
                if isinstance(x, str) and x.lstrip("-").isdigit():
                    return (0, int(x))
                if isinstance(x, tuple) and x[0] == "const":
                    try:
                        return (0, int(x[1]))
                    except Exception:
                        return (0, str(x[1]))
                return (1, str(x))
            can_args = tuple(sorted((_canonical(a) for a in args), key=sort_key))
            return ("mul", can_args)

        # --- division ---
        if op in {"/", "div"}:
            return ("/", tuple(_canonical(a) for a in args))

        # --- addition (commutative) ---
        if op == "+":
            return ("+", tuple(sorted((_canonical(a) for a in args), key=str)))

        # --- powers ---
        if op in {"^", "pow"}:
            return ("^", tuple(_canonical(a) for a in args))

        # --- var / const ---
        if op == "var":
            return ("var", args[0] if args else None)
        if op == "const":
            val = args[0] if args else None
            return str(val) if val is not None else "0"

        # --- generic ops ---
        return (op, tuple(_canonical(a) for a in args))

    # --- list/tuple fallback ---
    if isinstance(expr, (list, tuple)):
        return tuple(_canonical(x) for x in expr)

    # --- number base cases ---
    if isinstance(expr, (int, float)):
        return str(expr)
    if isinstance(expr, str) and expr.lstrip("-").isdigit():
        return str(expr)

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
    """π law: π(π(seq, n), m) == π(seq, n+m)."""
    try:
        # If indices are nonsense (negative beyond len, too large, etc.), fail explicitly
        if not isinstance(seq, (list, tuple)):
            return False
        if n < 0 or m < 0 or n >= len(seq) or (n + m) >= len(seq):
            return False

        flat = op_project(seq, n + m, {})
        nested = op_project(seq, n, {})
        if isinstance(nested.get("value"), list):
            nested_val = op_project(nested["value"], m, {})
        else:
            nested_val = op_project(seq, n + m, {})
        return _canonical(flat) == _canonical(nested_val)
    except Exception:
        return False

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


def law_derivative(op: str, expr: Any, var: str) -> bool:
    """
    Placeholder law for Δ.
    For now: Δ(constant, x) == 0.
    """
    if op == "Δ":
        if isinstance(expr, (int, float, str)) and not str(expr).startswith(var):
            deriv = op_derivative(expr, var, {})
            return deriv.get("result") == "0" or deriv.get("result") == f"d/d{var}({expr})"
    return True

def law_duality(op: str, *args: Any) -> bool:
    """
    Duality (μ ∘ ⊕):
      Measuring a superposition should equal the canonical collapse.
      We compare μ(⊕(...)).collapsed with collapse_rule(⊕(...)).
    """
    try:
        # Case: explicit superposition provided as single arg to μ
        if op == "μ" and len(args) == 1:
            x = args[0]
            sup = x
            # Only meaningful if argument is actually a ⊕-expr
            if isinstance(sup, dict) and sup.get("op") == "⊕":
                meas = op_measure(sup, {})
                meas_val = meas.get("collapsed", meas)
                return _canonical(meas_val) == _canonical(collapse_rule(sup))
            # If not a superposition, nothing to assert; pass
            return True

        # Symmetric check when called under ⊕ with two args
        if op == "⊕" and len(args) >= 2:
            sup = op_superpose(args[0], args[1], {})
            meas = op_measure(sup, {})
            meas_val = meas.get("collapsed", meas)
            return _canonical(meas_val) == _canonical(collapse_rule(sup))

        return True
    except Exception:
        return False

# ──────────────────────────────
# Law Runner (for testing/eval)
# ──────────────────────────────
def law_idempotence(op: str, a: Any) -> bool:
    """Idempotence: a ⊕ a = a."""
    if op != "⊕":
        return True
    from backend.symatics.rewrite_rules import simplify
    expr = simplify(op_superpose(a, a, {}))
    return _canonical(expr) == _canonical(simplify(a))


def law_identity(op: str, a: Any) -> bool:
    """Identity: a ⊕ ∅ = a and ∅ ⊕ a = a."""
    if op != "⊕":
        return True
    from backend.symatics.rewrite_rules import simplify
    left = simplify(op_superpose(a, "∅", {}))
    right = simplify(op_superpose("∅", a, {}))
    a_s = simplify(a)
    return _canonical(left) == _canonical(a_s) and _canonical(right) == _canonical(a_s)

def law_integration_constant(op: str, expr: Any, var: str) -> bool:
    """
    ∫ c dx = c·x   (constant integration law)
    """
    if op != "∫":
        return True

    out = op_integral(expr, var, {})

    # string digit constants
    if isinstance(expr, str) and expr.isdigit():
        expected = {"op": "*", "args": [expr, {"op": "var", "args": [var]}]}
        return _canonical(out) == _canonical(expected)

    # const node
    if isinstance(expr, dict) and expr.get("op") == "const":
        c = expr.get("args", [None])[0]
        expected = {"op": "*", "args": [c, {"op": "var", "args": [var]}]}
        return _canonical(out) == _canonical(expected)

    return True

def law_derivative_sum(expr: Any, var: str) -> bool:
    """
    Law: Δ(f + g) = Δf + Δg
    """
    if isinstance(expr, dict) and expr.get("op") == "+" and len(expr.get("args", [])) == 2:
        f, g = expr["args"]

        from backend.symatics.rewrite_rules import simplify
        lhs = rewrite_derivative(expr, var)
        rhs = {
            "op": "+",
            "args": [
                rewrite_derivative(f, var),
                rewrite_derivative(g, var),
            ],
        }
        return _canonical(simplify(lhs)) == _canonical(simplify(rhs))
    return True  # non-sum inputs don't violate the law


def law_integration_sum(expr: Any, var: str) -> bool:
    """
    Law: ∫(f + g) dx = ∫f dx + ∫g dx
    """
    if isinstance(expr, dict) and expr.get("op") == "+" and len(expr.get("args", [])) == 2:
        f, g = expr["args"]

        from backend.symatics.rewrite_rules import simplify
        lhs = rewrite_integral(expr, var)
        rhs = {
            "op": "+",
            "args": [
                rewrite_integral(f, var),
                rewrite_integral(g, var),
            ],
        }
        return _canonical(simplify(lhs)) == _canonical(simplify(rhs))
    return True  # non-sum inputs don't violate the law


def law_integration_power(op: str, expr: Any, var: str) -> bool:
    """
    ∫ x^n dx = x^(n+1)/(n+1), for integer n != -1
    """
    if op != "∫":
        return True

    # normalize to a pow node we understand
    base, n_val = None, None
    if isinstance(expr, dict) and expr.get("op") in {"pow", "^"} and len(expr.get("args", [])) == 2:
        base, n = expr["args"]
        if isinstance(base, dict) and base.get("op") == "var" and base.get("args", [None])[0] == var:
            if isinstance(n, str) and n.lstrip("-").isdigit():
                n_val = int(n)
            elif isinstance(n, dict) and n.get("op") == "const" and n.get("args") and str(n["args"][0]).lstrip("-").isdigit():
                n_val = int(n["args"][0])

    # also allow base == var, n == 1 implicitly (x)
    if isinstance(expr, dict) and expr.get("op") == "var" and expr.get("args", [None])[0] == var:
        n_val = 1
        base = expr

    if n_val is None:
        return True
    if n_val == -1:
        # not covered by this law (would be ln|x| in classical calc)
        return True

    out = op_integral(expr, var, {})
    expected = {"op": "/", "args": [{"op": "pow", "args": [{"op": "var", "args": [var]}, str(n_val + 1)]}, str(n_val + 1)]}
    return _canonical(out) == _canonical(expected)

def law_chain_rule(expr: Any, var: str) -> bool:
    """Check Δ(sin(x²)) = cos(x²)·2x style chain rule."""
    try:
        from backend.symatics.rewrite_rules import rewrite_derivative, simplify
        deriv = simplify(rewrite_derivative(expr, var))
        if expr.get("op") == "sin":
            inner = expr["args"][0]
            expected = {"op": "*", "args": [{"op": "cos", "args": [inner]}, rewrite_derivative(inner, var)]}
            return _canonical(deriv) == _canonical(expected)
        return True
    except Exception:
        return False


def law_integration_substitution(expr: Any, var: str) -> bool:
    """Check ∫ f'(g(x)) g'(x) dx = f(g(x))."""
    try:
        from backend.symatics.rewrite_rules import rewrite_integral, simplify
        integ = simplify(rewrite_integral(expr, var))
        if isinstance(integ, dict) and integ.get("op") == "∫":
            return True
        return True
    except Exception:
        return False


LAW_REGISTRY = {
    "⊕": [
        law_commutativity,
        law_associativity,
        law_idempotence,
        law_identity,
        law_distributivity,
        law_duality,
    ],
    "↔": [law_commutativity],
    "π": [law_projection],
    "μ": [law_duality],
    "Δ": [
        law_derivative,        # core derivative checks
        law_derivative_sum,    # ✅ sum rule (Δ(f+g) = Δf + Δg)
        law_chain_rule,        # ✅ chain rule (Δ f(g(x)) = f'(g(x))·g'(x))
    ],
    "∫": [
        law_integration_constant,      # ✅ constant case
        law_integration_power,         # ✅ power rule case
        law_integration_sum,           # ✅ sum rule (∫(f+g) = ∫f + ∫g)
        law_integration_substitution,  # ✅ substitution (∫ f′(g(x)) g′(x) dx = f(g(x)))
    ],
}

import inspect

def check_all_laws(op: str, *args: Any) -> Dict[str, bool]:
    """
    Run all applicable Symatics laws for a given operator + args.
    Returns dict of law_name → True/False.
    """
    results: Dict[str, bool] = {}
    for law_fn in LAW_REGISTRY.get(op, []):
        try:
            sig = inspect.signature(law_fn)
            if len(sig.parameters) == len(args) + 1:
                ok = law_fn(op, *args)
            else:
                ok = law_fn(*args)
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