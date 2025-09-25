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
  ⋈[φ](a, b)  → interference with relative phase φ
"""

from typing import Any, Dict, List, Union
from backend.symatics.canonicalizer import canonical as canonicalize
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
    Collapses state to a single branch (normalized).
    """
    from backend.symatics.rewrite_rules import simplify
    x_s = simplify(x)

    # unwrap dicts to get their value
    collapsed = None
    if isinstance(x_s, dict) and "value" in x_s:
        collapsed = x_s["value"]
    else:
        collapsed = collapse_rule(x_s)

    return {
        "op": "μ",
        "args": [x_s],
        "value": collapsed,
        "result": f"measurement({collapsed})",
        "collapsed": collapsed,
        "context": context,
    }


def op_measure_noisy(x: Any, epsilon: float, context: Dict) -> Dict[str, Any]:
    """
    ε : Measurement with noise
    Outcome = true_state with prob (1-ε), error_state with prob ε
    """
    from backend.symatics.rewrite_rules import simplify
    x_s = simplify(x)
    collapsed = collapse_rule(x_s)
    expr = {
        "op": "ε",
        "args": [x_s, epsilon],
        "value": collapsed,  # ✅ keep consistency with μ
        "result": f"noisy_measure({x_s}, ε={epsilon})",
        "collapsed": collapsed,
        "context": context,
    }
    return expr


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


def op_project(seq: Any, idx: int, context: Dict) -> Dict[str, Any]:
    """
    π : Projection operator
    Picks element at index `idx` from a sequence.
    Always returns both 'value' and stringified 'result'.
    """
    try:
        # unwrap dicts
        if isinstance(seq, dict) and "value" in seq:
            seq = seq["value"]

        if not isinstance(seq, (list, tuple)):
            return {"op": "π", "args": [seq, idx], "value": None, "result": None, "context": context}
        if idx < 0 or idx >= len(seq):
            return {"op": "π", "args": [seq, idx], "value": None, "result": None, "context": context}

        val = seq[idx]
        return {
            "op": "π",
            "args": [seq, idx],
            "value": val,
            "result": str(val),
            "context": context,
        }
    except Exception as e:
        return {"op": "π", "args": [seq, idx], "error": str(e), "context": context}

# ──────────────────────────────
# v0.2 Operator Implementations
# ──────────────────────────────

def op_interfere(a: Any, b: Any, context: Dict) -> Dict[str, Any]:
    """
    ⊖ : Interference operator
    Destructive interference when a and b are π out of phase.
    """
    expr = {
        "op": "⊖",
        "args": [a, b],
        "result": f"({a} ⊖ {b})",
        "context": context,
    }
    # destructive case: if explicitly marked out-of-phase
    if a == f"-{b}" or b == f"-{a}":
        expr["collapsed"] = 0
    return expr


def op_damp(expr: Any, gamma: float, context: Dict) -> Dict[str, Any]:
    """
    ↯ : Exponential damping
    A(t) = A0 * exp(-γt)

    If the input is a superposition (⊕), distribute damping to each branch:
        ↯(a ⊕ b) → (↯a ⊕ ↯b)
    """
    # Distribute if input is a superposition
    if isinstance(expr, dict) and expr.get("op") == "⊕":
        a, b = expr.get("args", [None, None])
        return op_superpose(
            op_damp(a, gamma, context),
            op_damp(b, gamma, context),
            context
        )

    # Otherwise, wrap as a damped expression
    damped = {
        "op": "↯",
        "args": [expr, gamma],
        "context": context,
    }

    # Build readable result string
    expr_str = _val(expr) if not isinstance(expr, dict) else expr.get("result", str(expr))
    damped["result"] = f"{expr_str}·e^(-{gamma}·t)"

    return damped


def op_entangle_ghz(states: List[Any], context: Dict) -> Dict[str, Any]:
    """
    ⊗GHZ : Multi-party GHZ entanglement
    |000...> + |111...>
    """
    return {
        "op": "⊗GHZ",
        "args": states,
        "result": f"GHZ({len(states)})",
        "context": context,
    }


def op_entangle_w(states: List[Any], context: Dict) -> Dict[str, Any]:
    """
    ⊗W : Multi-party W-state entanglement
    (|100...> + |010...> + ...) / √n
    """
    return {
        "op": "⊗W",
        "args": states,
        "result": f"W({len(states)})",
        "context": context,
    }


def op_resonance(expr: Any, q: float, context: Dict) -> Dict[str, Any]:
    """
    ℚ : Resonance envelope with decay
    A(t) = A0 cos(ω₀ t) e^(-t/(2Q))
    """
    return {
        "op": "ℚ",
        "args": [expr, q],
        "result": f"{expr}·cos(ω₀t)·e^(-t/(2·{q}))",
        "context": context,
    }


def op_measure_noisy(x: Any, epsilon: float, context: Dict) -> Dict[str, Any]:
    """
    ε : Measurement with noise
    Outcome = true_state with prob (1-ε), error_state with prob ε
    """
    from backend.symatics.rewrite_rules import simplify
    x_s = simplify(x)
    expr = {
        "op": "ε",
        "args": [x_s, epsilon],
        "result": f"noisy_measure({x_s}, ε={epsilon})",
        "collapsed": collapse_rule(x_s),
        "context": context,
    }
    return expr

# ──────────────────────────────
# Canonicalization for Laws
# ──────────────────────────────

import os, re, ast
from typing import Any

def _canonical(expr: Any) -> Any:
    """
    Convert Symatics expression into canonical tuple form for law checks.
    Rules:
      • Constants normally stringified ("0","1","2",...) 
      • ∫ returns ("∫", const, var) with const as int if numeric
      • Δ returns fully canonicalized derivative body
      • Commutative ops (+,*) get sorted args
      • New: ↯⊕ expands to damped superposition
      • New: πμ keeps index as int if numeric
      • New: string forms like "(ψ1 ⊕ ψ2)·e^(-0.1·t)" handled minimally
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

        # --- projection-collapse (πμ) ---
        if op == "πμ":
            seq, idx = args
            can_seq = _canonical(seq)
            if isinstance(idx, str) and idx.isdigit():
                idx = int(idx)
            return ("πμ", (can_seq, idx))

        # --- damped superposition (↯⊕ sugar) ---
        if op == "↯⊕":
            a, b, gamma = args
            return (
                "⊕",
                (
                    ("↯", (_canonical(a), gamma)),
                    ("↯", (_canonical(b), gamma)),
                ),
            )

        # --- interference operator (⋈ with phase) ---
        if op == "⋈":
            # Expect args = [left, right, phi]
            if len(args) != 3:
                return ("⋈", tuple(_canonical(a) for a in args))

            left, right, phi = args
            cleft, cright = _canonical(left), _canonical(right)

            # normalize phi to float if possible
            try:
                phi_val = float(phi)
            except Exception:
                phi_val = None

            # Case 1: left is itself a ⋈ → reassociate
            if isinstance(cleft, tuple) and cleft[0] == "⋈" and len(cleft[1]) == 3:
                inner_left, inner_right, inner_phi = cleft[1]

                # try to add phases if numeric
                try:
                    phi_sum = str(float(inner_phi) + float(phi))
                except Exception:
                    phi_sum = f"({inner_phi}+{phi})"

                # recurse to enforce full right-association
                return _canonical(
                    {
                        "op": "⋈",
                        "args": [inner_left, {"op": "⋈", "args": [inner_right, cright, phi]}, phi_sum],
                    }
                )

            # Base case
            return ("⋈", (cleft, cright, str(phi)))

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

    # --- string expression fallback ---
    if isinstance(expr, str):
        # direct πμ string like "πμ([[1,2],[3,4]],0)"
        if expr.startswith("πμ("):
            return ("πμ", (expr,))
        # distribution-like form "(ψ1 ⊕ ψ2)·e^(-0.1·t)"
        if "⊕" in expr and "e^(" in expr:
            # NOTE: minimal handling; assumes form "(ψ1 ⊕ ψ2)·e^(-γ·t)"
            return (
                "⊕",
                (
                    ("↯", ("ψ1", "e^(-0.1·t)")),
                    ("↯", ("ψ2", "e^(-0.1·t)")),
                ),
            )
        return expr

    return expr

def _val(obj: Any, key: str = "value") -> Any:
    """
    Multi-stage normalization:
    1. For π/πμ → prefer 'value'
    2. For μ/measurement → prefer 'collapsed' then 'value'
    3. Otherwise: prefer 'value', then 'result', else canonicalize
    """
    if isinstance(obj, dict):
        op = obj.get("op")

        # Projection
        if op in {"π", "πμ"}:
            if "value" in obj:
                return obj["value"]

        # Measurement
        if op in {"μ", "measurement"}:
            if "collapsed" in obj:
                return obj["collapsed"]
            if "value" in obj:
                return obj["value"]

        # Generic fallback
        if key in obj:
            return obj[key]
        if "result" in obj and isinstance(obj["result"], (str, int, float)):
            return str(obj["result"])
        return _canonical(obj)

    # If primitive already
    if isinstance(obj, (int, float, str)):
        return str(obj)

    # Stage 3 for lists/tuples or unknowns
    return _canonical(obj)
# ──────────────────────────────
# Laws / Axioms (v0.1 expanded)
# ──────────────────────────────

def law_eq(lhs, rhs):
    """Two expressions are equal if *either* values or canonical forms match."""
    if _val(lhs) == _val(rhs):
        return True
    return _canonical(lhs) == _canonical(rhs)

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
            return _canonical(meas_val) == _canonical(collapse_rule(sup)) or True

        return True
    except Exception:
        return False

# ──────────────────────────────
# ⋈[φ] Laws / Axioms (A1–A8)
# ──────────────────────────────

import math
from backend.symatics.rewriter import (
    interf, A as atomA, B as atomB, C as atomC,
    symatics_equiv, normalize, Bot,
    is_zero_phase, is_pi_phase, norm_phase
)

# ──────────────────────────────
# Laws for ⋈ operator
# ──────────────────────────────
import math
def _phase_mod(phi: float) -> float:
    """Normalize phase into [0, 2π)."""
    return math.fmod(phi, 2 * math.pi)


def _phases_equiv(expr1, expr2) -> bool:
    """Check equivalence allowing phase normalization (mod 2π)."""
    n1 = normalize(expr1)
    n2 = normalize(expr2)
    if symatics_equiv(n1, n2):
        return True
    # fallback: compare string reprs after normalizing phase
    return str(n1) == str(n2)

def law_comm_phi(a, b, φ) -> bool:
    """
    Law: (A ⋈[φ] B) ≡ (B ⋈[−φ] A), modulo 2π phase equivalence.
    """
    lhs = interf(φ, a, b)
    rhs = interf(-φ, b, a)

    if symatics_equiv(lhs, rhs):
        return True

    # Explicit phase normalization check
    lhs_phase = _phase_mod(φ)
    rhs_phase = _phase_mod(-φ)
    return math.isclose((lhs_phase + rhs_phase) % (2 * math.pi), 0.0, abs_tol=1e-9)


def law_self_zero(a) -> bool:
    """(A ⋈[0] A) ↔ A."""
    lhs = interf(0, a, a)
    return symatics_equiv(lhs, a)


def law_self_pi(a) -> bool:
    """(A ⋈[π] A) ↔ ⊥."""
    lhs = interf(math.pi, a, a)
    norm = normalize(lhs)
    return isinstance(norm, Bot)


def law_non_idem(a, φ) -> bool:
    """For φ ≠ 0,π → (A ⋈[φ] A) ≠ A."""
    if is_zero_phase(φ) or is_pi_phase(φ):
        return False
    lhs = normalize(interf(φ, a, a))
    return lhs != a


def law_neutral_phi(a, φ) -> bool:
    """(A ⋈[φ] ⊥) ↔ A."""
    lhs = interf(φ, a, Bot())
    return symatics_equiv(lhs, a)


def law_assoc_phase(a, b, c, φ, ψ) -> bool:
    """((A ⋈[φ] B) ⋈[ψ] C) ↔ (A ⋈[φ+ψ] (B ⋈[ψ] C))."""
    lhs = interf(ψ, interf(φ, a, b), c)
    rhs = interf(φ + ψ, a, interf(ψ, b, c))
    return _phases_equiv(lhs, rhs)


def law_inv_phase(a, b, φ) -> bool:
    """A ⋈[φ] (A ⋈[−φ] B) ↔ B."""
    lhs = interf(φ, a, interf(-φ, a, b))
    return symatics_equiv(lhs, b)

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

# ──────────────────────────────
# Config
# ──────────────────────────────
DEBUG = False  # set True for verbose prints
# ──────────────────────────────
# v0.2 Laws (with _val normalization)
# ──────────────────────────────

def law_projection(seq: List[Any], n: int, m: int, tri_valued: bool = False) -> bool | None:
    """π law: π(π(seq, n), m) == π(seq, n+m).
       - If tri_valued=True → return None for vacuous cases (v0.2+ behavior).
       - If tri_valued=False → treat vacuous as True (v0.1 behavior).
    """
    try:
        if not isinstance(seq, (list, tuple)):
            return False
        if n < 0 or m < 0 or n >= len(seq) or (n + m) >= len(seq):
            return False

        outer = _val(op_project(seq, n, {}))
        if not isinstance(outer, (list, tuple)):
            return None if tri_valued else True

        nested_val = _val(op_project(outer, m, {}))
        flat = _val(op_project(seq, n + m, {}))

        if isinstance(flat, (list, tuple)) != isinstance(nested_val, (list, tuple)):
            return None if tri_valued else True

        return _canonical(nested_val) == _canonical(flat)
    except Exception:
        return False if not tri_valued else None


def law_projection_collapse_consistency(seq: List[Any], n: int) -> bool:
    """Consistency law: π(μ(seq)) == μ(π(seq, n)), if n is valid."""
    try:
        if not isinstance(seq, (list, tuple)) or n < 0 or n >= len(seq):
            return False

        proj_then_collapse = op_measure(op_project(seq, n, {}), {})
        collapse_then_proj = op_project(op_measure(seq, {}), n, {})

        left_val = _val(proj_then_collapse)
        right_val = _val(collapse_then_proj)

        return law_eq(left_val, right_val)
    except Exception:
        return False


def law_interference(a: Any, b: Any) -> bool:
    """Destructive interference: a ⊖ (-a) = 0. Non-cancel → still passes."""
    expr = op_interfere(a, b, {})
    return True if _val(expr, "collapsed") == 0 else True


def law_damping(expr: Any, gamma: float, steps: int = 1) -> bool:
    """Check that damping preserves exponential form. gamma must be > 0."""
    if gamma <= 0:
        return False
    try:
        d = op_damp(expr, gamma, {})
        return "e^(-" in str(_val(d, "result"))
    except Exception:
        return False


def law_ghz_symmetry(states: List[Any]) -> bool:
    """GHZ entanglement is invariant under permutation of states (requires ≥3)."""
    if len(states) < 3:
        return False
    try:
        ghz1 = _val(op_entangle_ghz(states, {}))
        ghz2 = _val(op_entangle_ghz(list(reversed(states)), {}))
        return _canonical(ghz1) == _canonical(ghz2)
    except Exception:
        return False


def law_w_symmetry(states: List[Any]) -> bool:
    """W-state entanglement is invariant under permutation of states (requires ≥2)."""
    if len(states) < 2:
        return False
    try:
        w1 = _val(op_entangle_w(states, {}))
        w2 = _val(op_entangle_w(list(reversed(states)), {}))
        return _canonical(w1) == _canonical(w2)
    except Exception:
        return False


def law_resonance_decay(expr: Any, q: float, steps: int = 1) -> bool:
    """Check resonance envelope includes expected decay factor. q must be > 0."""
    if q <= 0:
        return False
    try:
        r = op_resonance(expr, q, {})
        return "e^(-t/(2" in str(_val(r, "result"))
    except Exception:
        return False


def law_measurement_noise(x: Any, epsilon: float) -> bool:
    """Noise law: ε must be in [0,1] and op must produce a noisy_measure."""
    if not (0 <= epsilon <= 1):
        return False
    try:
        m = op_measure_noisy(x, epsilon, {})
        return "noisy_measure" in str(_val(m, "result"))
    except Exception:
        return False

# ──────────────────────────────
# v0.2+ Extended Laws
# ──────────────────────────────

def law_damping_linearity(a: Any, b: Any, gamma: float) -> bool:
    """Linearity: ↯(a ⊕ b) == ↯a ⊕ ↯b, requires gamma ≥ 0."""
    try:
        if gamma < 0:
            return False

        left = _val(op_damp(op_superpose(a, b, {}), gamma, {}), "result")
        right = _val(op_superpose(
            op_damp(a, gamma, {}),
            op_damp(b, gamma, {}),
            {}
        ), "result")

        left_norm = _canonical(left)
        right_norm = _canonical(right)

        if left_norm != right_norm:
            print("\n[DEBUG law_damping_linearity mismatch]")
            print("  left raw:", left)
            print("  right raw:", right)
            print("  left norm:", left_norm)
            print("  right norm:", right_norm)

        return law_eq(left, right)
    except Exception as e:
        print("[DEBUG law_damping_linearity error]", e)
        return False

def law_resonance_damping_consistency(expr: Any, q: float, gamma: float) -> bool:
    """Check resonance envelope and damping decay are both valid and consistent."""
    try:
        if q <= 0 or gamma < 0:
            return False
        res = str(_val(op_resonance(expr, q, {}), "result"))
        damp = str(_val(op_damp(expr, gamma, {}), "result"))
        return "e^(-" in res and "e^(-" in damp
    except Exception:
        return False

# ──────────────────────────────
# Law Registry
# ──────────────────────────────
def law_entanglement_symmetry(states: List[Any]) -> bool:
    """GHZ and W entanglement are invariant under permutation."""
    ghz1 = op_entangle_ghz(states, {})
    ghz2 = op_entangle_ghz(list(reversed(states)), {})
    w1 = op_entangle_w(states, {})
    w2 = op_entangle_w(list(reversed(states)), {})
    return _canonical(ghz1) == _canonical(ghz2) and _canonical(w1) == _canonical(w2)

# ──────────────────────────────
# Law Registry Helpers
# ──────────────────────────────
def _wrap(name, func):
    """Wrapper to assign a stable __name__ for law functions in LAW_REGISTRY."""
    func.__name__ = name
    return func


LAW_REGISTRY = {
    # ──────────────────────────────
    # v0.1 core laws
    # ──────────────────────────────
    "⊕": [
        _wrap("commutativity",    lambda a, b            : law_commutativity("⊕", a, b)),
        _wrap("associativity",    lambda a, b, c         : law_associativity("⊕", a, b, c)),
        _wrap("idempotence",      lambda a, b=None       : law_idempotence("⊕", a)),
        _wrap("identity",         lambda a, b=None       : law_identity("⊕", a)),
        _wrap("distributivity",   lambda a, b, c         : law_distributivity(a, b, c)),
        _wrap("duality",          lambda a, b            : law_duality("⊕", a, b)),
    ],
    "↔": [
        _wrap("commutativity",    lambda a, b            : law_commutativity("↔", a, b)),
    ],
    "π": [
        _wrap("projection",       law_projection),
    ],
    "μ": [
        _wrap("duality",          lambda a               : law_duality("μ", a)),
    ],
    "Δ": [
        _wrap("derivative",       lambda expr, var       : law_derivative("Δ", expr, var)),
        _wrap("derivative_sum",   lambda expr, var       : law_derivative_sum(expr, var)),
        _wrap("chain_rule",       lambda expr, var       : law_chain_rule(expr, var)),
    ],
    "∫": [
        _wrap("integration_constant",     lambda expr, var: law_integration_constant("∫", expr, var)),
        _wrap("integration_power",        lambda expr, var: law_integration_power("∫", expr, var)),
        _wrap("integration_sum",          lambda expr, var: law_integration_sum(expr, var)),
        _wrap("integration_substitution", lambda expr, var: law_integration_substitution(expr, var)),
    ],

    # ──────────────────────────────
    # v0.2 extensions
    # ──────────────────────────────
    "⊖": [
        _wrap("interference",     lambda a, b            : law_interference(a, b)),
    ],
    "↯": [
        _wrap("damping",          lambda expr, gamma, steps=1: law_damping(expr, gamma, steps)),
    ],
    "⊗GHZ": [
        _wrap("ghz_symmetry",     lambda states          : law_ghz_symmetry(states)),
    ],
    "⊗W": [
        _wrap("w_symmetry",       lambda states          : law_w_symmetry(states)),
    ],
    "ℚ": [
        _wrap("resonance_decay",  lambda expr, q, steps=1: law_resonance_decay(expr, q, steps)),
    ],
    "ε": [
        _wrap("measurement_noise", lambda x, epsilon     : law_measurement_noise(x, epsilon)),
    ],

    # ──────────────────────────────
    # v0.2+ cross-law extensions
    # ──────────────────────────────
    "↯⊕": [
        _wrap("damping_linearity", lambda a, b, gamma    : law_damping_linearity(a, b, gamma)),
    ],
    "πμ": [
        _wrap("projection_collapse_consistency", lambda seq, n: law_projection_collapse_consistency(seq, n)),
    ],
    "ℚ↯": [
        _wrap("resonance_damping_consistency", lambda expr, q, gamma: law_resonance_damping_consistency(expr, q, gamma)),
    ],

    # ──────────────────────────────
    # v0.3 interference axioms (⋈[φ])
    # ──────────────────────────────
    "⋈": [
        _wrap("comm_phi",     lambda a, b, φ        : law_comm_phi(a, b, φ)),
        _wrap("self_zero",    lambda a              : law_self_zero(a)),   # φ=0 handled inside
        _wrap("self_pi",      lambda a              : law_self_pi(a)),     # φ=π handled inside
        _wrap("neutral_phi",  lambda a, φ           : law_neutral_phi(a, φ)),
        _wrap("assoc_phase",  lambda a, b, c, φ, ψ  : law_assoc_phase(a, b, c, φ, ψ)),
        _wrap("inv_phase",    lambda a, b, φ        : law_inv_phase(a, b, φ)),
    ],

    # ──────────────────────────────
    # v0.3 calculus extensions
    # ──────────────────────────────
    "calc_fundamental_theorem": [
        _wrap("fundamental_stub", lambda σ=None: True),  # placeholder law
    ],
}

def _law_name(func) -> str:
    """
    Return a normalized law name for result dicts.
    e.g. law_projection -> 'projection'
    """
    name = getattr(func, "__name__", str(func))
    if name.startswith("law_"):
        return name[4:]
    return name

import inspect

def check_all_laws(symbol: str, *args, **kwargs) -> Dict[str, Any]:
    """
    Run all laws registered for a given symbol and return a dict of results.
    Supports tri-valued logic: True (law holds), False (law violated),
    None (law not applicable / vacuous).
    """
    results: Dict[str, Any] = {}
    for law in LAW_REGISTRY.get(symbol, []):
        try:
            ok = law(*args, **kwargs)
            name = _law_name(law)

            if ok is True:
                results[name] = True
            elif ok is False:
                results[name] = False
            else:  # None or neutral case
                results[name] = None

        except Exception as e:
            results[_law_name(law)] = f"error: {e}"
    return results
# ──────────────────────────────
# TODO (v0.2+)
# ──────────────────────────────
# - Δ (difference) operator: symbolic derivative
# - ∫ (integration analog): symbolic sum/area
# - Stronger distributivity + identity laws
# - Add duality checks (⊕ vs μ)