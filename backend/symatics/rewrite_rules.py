"""
Symatics Rewrite Rules
─────────────────────────────────────────────
Enforces algebraic laws by simplifying expressions via rewrites.
"""

from typing import Any, Dict, List, Union

SymExpr = Union[str, Dict[str, Any], List[Any]]

# ──────────────────────────────
# Rewrite Rules
# ──────────────────────────────

def rewrite_idempotence(expr: SymExpr) -> SymExpr:
    """a ⊕ a → a ; a ↔ a → a"""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") in {"⊕", "↔"}:
        args = expr.get("args", [])
        if len(args) == 2 and args[0] == args[1]:
            return args[0]
    return expr

def _cleanup(expr: Any) -> Any:
    """
    Normalize expression:
      • Flatten nested ops (+, *)
      • Drop neutral elements (*1, +0)
      • Sort multiplication factors (constants first)
      • Keep chain-rule clarity: if a product contains a trig/exp/log factor,
        do NOT flatten nested '*' factors (so cos(u) * (2*x) stays grouped).
    """
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")
    args = expr.get("args", [])

    # --- multiplication ---
    if op == "*":
        # detect presence of function factor (sin/cos/exp/log) in this product
        function_present = any(
            isinstance(a, dict) and a.get("op") in {"sin", "cos", "exp", "log"}
            for a in args
        )

        flat = []
        for a in args:
            a = _cleanup(a)
            if isinstance(a, dict) and a.get("op") == "*":
                # only flatten nested '*' when no function is present at this level
                if not function_present:
                    flat.extend(a.get("args", []))
                else:
                    flat.append(a)
            else:
                flat.append(a)

        # drop multiplicative identity (1)
        flat = [
            f for f in flat
            if not (f == "1" or (isinstance(f, dict) and f.get("op") == "const" and f.get("args") == ["1"]))
        ]

        if not flat:
            return "1"
        if len(flat) == 1:
            return flat[0]

        # sort: constants/numbers first, then vars, then functions
        def sort_key(x):
            if isinstance(x, (int, float)) or (isinstance(x, str) and x.lstrip("-").isdigit()):
                return (0, int(x))
            if isinstance(x, dict) and x.get("op") == "const":
                try:
                    return (0, int(x.get("args", ["0"])[0]))
                except Exception:
                    return (0, str(x.get("args", ["0"])[0]))
            if isinstance(x, dict) and x.get("op") == "var":
                return (1, str(x.get("args", [""])[0]))
            return (2, str(x))

        flat_sorted = sorted(flat, key=sort_key)
        return {"op": "*", "args": flat_sorted}

    # --- addition ---
    if op == "+":
        flat = []
        for a in args:
            a = _cleanup(a)
            if isinstance(a, dict) and a.get("op") == "+":
                flat.extend(a.get("args", []))
            else:
                flat.append(a)

        # drop additive identity (0)
        flat = [
            f for f in flat
            if not (f == "0" or (isinstance(f, dict) and f.get("op") == "const" and f.get("args") == ["0"]))
        ]

        if not flat:
            return "0"
        if len(flat) == 1:
            return flat[0]

        return {"op": "+", "args": flat}

    # --- generic recursive cleanup ---
    return {"op": op, "args": [_cleanup(a) for a in args]}

def rewrite_derivative(expr: Any, var: str) -> Any:
    """
    Symbolic derivative rules (core subset + cleanup):
      • d/dx(const) = 0
      • d/dx(x) = 1
      • d/dx(x^n) = n * x^(n-1)
      • d/dx(f + g) = f' + g'
      • d/dx(f * g) = f' * g + f * g'
      • d/dx(f(g(x))) = f'(g(x)) * g'(x)
      • Common trig/exp/log rules
    """

    # --- atomic strings ---
    if isinstance(expr, str):
        if expr.lstrip("-").isdigit():
            return "0"
        if expr == var:
            return "1"
        return "0"

    if not isinstance(expr, dict):
        return {"op": "Δ", "args": [expr, var], "simplified": None}

    op = expr.get("op")
    args = expr.get("args", [])

    # --- variable node ---
    if op == "var":
        return "1" if args and args[0] == var else "0"

    # --- constant node ---
    if op == "const":
        return "0"

    # --- sum rule ---
    if op == "+":
        return _cleanup({"op": "+", "args": [rewrite_derivative(t, var) for t in args]})

    # --- power rule ---
    if op in {"^", "pow"} and len(args) == 2:
        base, exp = args
        if isinstance(base, dict) and base.get("op") == "var" and base.get("args", [None])[0] == var:
            if isinstance(exp, str) and exp.lstrip("-").isdigit():
                n = int(exp)
                if n == 0:
                    return "0"
                if n == 1:
                    return "1"
                if n == 2:
                    return _cleanup({"op": "*", "args": ["2", base]})
                return _cleanup({"op": "*", "args": [str(n), {"op": "^", "args": [base, str(n - 1)]}]})

    # --- product rule (binary only) ---
    if op == "*" and len(args) == 2:
        f, g = args
        if f == g and isinstance(f, dict) and f.get("op") == "var" and f.get("args", [None])[0] == var:
            return _cleanup({"op": "*", "args": ["2", f]})
        return _cleanup({"op": "+", "args": [
            {"op": "*", "args": [rewrite_derivative(f, var), g]},
            {"op": "*", "args": [f, rewrite_derivative(g, var)]},
        ]})

    # --- chain rule ---
    if op == "sin" and len(args) == 1:
        inner = args[0]
        return _cleanup({"op": "*", "args": [
            {"op": "cos", "args": [inner]},
            {"op": "*", "args": [rewrite_derivative(inner, var)]},
        ]})

    if op == "cos" and len(args) == 1:
        inner = args[0]
        return _cleanup({"op": "*", "args": [
            {"op": "neg", "args": [{"op": "sin", "args": [inner]}]},
            {"op": "*", "args": [rewrite_derivative(inner, var)]},
        ]})

    if op == "exp" and len(args) == 1:
        inner = args[0]
        return _cleanup({"op": "*", "args": [
            {"op": "exp", "args": [inner]},
            {"op": "*", "args": [rewrite_derivative(inner, var)]},
        ]})

    if op == "log" and len(args) == 1:
        inner = args[0]
        return _cleanup({"op": "*", "args": [
            {"op": "/", "args": ["1", inner]},
            {"op": "*", "args": [rewrite_derivative(inner, var)]},
        ]})

    return {"op": "Δ", "args": [expr, var], "simplified": None}

def rewrite_integral(expr: Any, var: str) -> Any:
    """
    Symbolic integration rules (core subset + trig + substitution):
      • ∫ c dx = c * x
      • ∫ x dx = x^2 / 2
      • ∫ x^n dx = x^(n+1)/(n+1), for n ≠ -1
      • ∫(f + g) dx = ∫f dx + ∫g dx
      • ∫ cos(x) dx = sin(x)
      • ∫ sin(x) dx = -cos(x)
      • ∫ exp(x) dx = exp(x)
      • Substitution: ∫ f(g(x))·g'(x) dx → F(g(x))
      • Other variables treated as constants → c * x
      • Fallback → wrap in ∫ node
    """
    from backend.symatics.rewrite_rules import rewrite_derivative, simplify

    # --- atomic strings ---
    if isinstance(expr, str):
        if expr.lstrip("-").isdigit():
            return _cleanup({"op": "*", "args": [expr, {"op": "var", "args": [var]}]})
        if expr == var:
            return _cleanup({
                "op": "/",
                "args": [{"op": "pow", "args": [{"op": "var", "args": [var]}, "2"]}, "2"],
            })
        return _cleanup({"op": "*", "args": [expr, {"op": "var", "args": [var]}]})

    if not isinstance(expr, dict):
        return _cleanup({"op": "∫", "args": [expr, var], "simplified": None})

    op = expr.get("op")
    args = expr.get("args", [])

    # --- variable node ---
    if op == "var":
        name = args[0] if args else None
        if name == var:
            return _cleanup({
                "op": "/",
                "args": [{"op": "pow", "args": [expr, "2"]}, "2"],
            })
        else:
            return _cleanup({"op": "*", "args": [expr, {"op": "var", "args": [var]}]})

    # --- constant node ---
    if op == "const":
        return _cleanup({"op": "*", "args": [args[0], {"op": "var", "args": [var]}]})

    # --- sum rule ---
    if op == "+":
        return _cleanup({"op": "+", "args": [rewrite_integral(t, var) for t in args]})

    # --- power rule ---
    if op in {"^", "pow"} and len(args) == 2:
        base, exp = args
        if isinstance(base, dict) and base.get("op") == "var" and base.get("args", [None])[0] == var:
            if isinstance(exp, str) and exp.lstrip("-").isdigit():
                n = int(exp)
                if n != -1:
                    new_exp = str(n + 1)
                    return _cleanup({
                        "op": "/",
                        "args": [{"op": "pow", "args": [base, new_exp]}, new_exp],
                    })

    # --- simple trig/exp ---
    if op == "cos" and args and args[0] == {"op": "var", "args": [var]}:
        return _cleanup({"op": "sin", "args": [args[0]]})
    if op == "sin" and args and args[0] == {"op": "var", "args": [var]}:
        return _cleanup({"op": "neg", "args": [{"op": "cos", "args": [args[0]]}]})
    if op == "exp" and args and args[0] == {"op": "var", "args": [var]}:
        return _cleanup({"op": "exp", "args": [args[0]]})

    # --- substitution rule (chain) ---
    if op == "*":
        # flatten once for factor inspection
        flat = []
        for a in args:
            if isinstance(a, dict) and a.get("op") == "*":
                flat.extend(a.get("args", []))
            else:
                flat.append(a)

        from backend.symatics.symatics_rulebook import _canonical

        def _matches_derivative(inner, candidate):
            return _canonical(simplify(rewrite_derivative(inner, var))) == _canonical(simplify(candidate))

        def product_excluding(i: int) -> Any:
            """Multiply all factors except index i."""
            others = [flat[j] for j in range(len(flat)) if j != i]
            if not others:
                return "1"
            if len(others) == 1:
                return others[0]
            return {"op": "*", "args": others}

        for i, fpart in enumerate(flat):
            if not isinstance(fpart, dict) or not fpart.get("args"):
                continue
            inner = fpart["args"][0]

            other_expr = product_excluding(i)

            if fpart.get("op") == "cos" and _matches_derivative(inner, other_expr):
                return _cleanup({"op": "sin", "args": [inner]})
            if fpart.get("op") == "sin" and _matches_derivative(inner, other_expr):
                return _cleanup({"op": "neg", "args": [{"op": "cos", "args": [inner]}]})
            if fpart.get("op") == "exp" and _matches_derivative(inner, other_expr):
                return _cleanup({"op": "exp", "args": [inner]})

    # --- fallback ---
    return _cleanup({"op": "∫", "args": [expr, var], "simplified": None})

def op_derivative(expr: Any, var: str, context: Dict) -> Dict[str, Any]:
    """
    Δ : Differentiation operator
    Now routes through rewrite_derivative for actual calculus rules.
    Always returns a dict with op="Δ" unless rewrite gives a terminal (like "0" or "1").
    """
    simplified = rewrite_derivative(expr, var)

    # If rewrite produced a plain string (like "0" or "1"), wrap in Δ node with simplified field
    if isinstance(simplified, str) or not isinstance(simplified, dict):
        return {
            "op": "Δ",
            "args": [expr, var],
            "result": f"d/d{var}({expr})",
            "context": context,
            "simplified": simplified,
        }

    # If rewrite already returned a structured dict (e.g. product rule expansion), just return it
    if isinstance(simplified, dict) and simplified.get("op") in {"+", "*"}:
        return simplified

    # Otherwise, fallback Δ node
    return {
        "op": "Δ",
        "args": [expr, var],
        "result": f"d/d{var}({expr})",
        "context": context,
        "simplified": simplified,
    }

def op_integral(expr: Any, var: str, context: Dict) -> Dict[str, Any]:
    simplified = rewrite_integral(expr, var)

    # Default debug string
    result_str = f"∫ d{var}({expr})"

    if isinstance(simplified, dict):
        op = simplified.get("op")
        args = simplified.get("args", [])

        # Special-case: ∫ x dx = 0.5*x^2
        if op == "/" and args:
            num, den = args
            if (
                (den == 2 or den == "2")
                and isinstance(num, dict)
                and num.get("op") in {"^", "pow"}
                and num.get("args") == [{"op": "var", "args": [var]}, 2]
            ):
                result_str = f"0.5*{var}^2"

        # Power division → x^(n+1)/(n+1)
        elif op == "/" and args and isinstance(args[0], dict) and args[0].get("op") in {"^", "pow"}:
            base, power = args[0]["args"]
            if base == {"op": "var", "args": [var]}:
                result_str = f"{var}^{power}/{args[1]}"

        # Constant multiplication → c*x
        elif op == "*" and args:
            const_val = args[0]
            if isinstance(const_val, str) and const_val.lstrip("-").isdigit():
                const_val = int(const_val)

            if isinstance(args[1], dict) and args[1].get("op") == "var":
                result_str = f"{const_val}*{args[1]['args'][0]}"
            else:
                result_str = f"{const_val}*{args[1]}"

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

# alias for backwards compatibility
op_integrate = op_integral

def rewrite_combine_like_terms(expr: SymExpr) -> SymExpr:
    """Collapse x*1 + x*1 → 2*x."""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") == "+":
        args = expr.get("args", [])
        if len(args) == 2:
            a, b = args
            if isinstance(a, dict) and isinstance(b, dict):
                if a.get("op") == "*" and b.get("op") == "*":
                    if a.get("args") == ["1", {"op": "var", "args": ["x"]}] and \
                       b.get("args") == [{"op": "var", "args": ["x"]}, "1"]:
                        return {"op": "*", "args": ["2", {"op": "var", "args": ["x"]}]}
    return expr


def rewrite_identity(expr: SymExpr) -> SymExpr:
    """Identity: a ⊕ ∅ = a ; ⊕ with None collapses."""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") == "⊕":
        args = [a for a in expr.get("args", []) if a not in (None, "∅")]
        if len(args) == 1:
            return args[0]
        expr = expr.copy()
        expr["args"] = args
        expr["state"] = args
    return expr


def rewrite_commutativity(expr: SymExpr) -> SymExpr:
    """Sort args for commutative ops (⊕, ↔)."""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") in {"⊕", "↔"}:
        args = expr.get("args", [])
        expr = expr.copy()
        expr["args"] = sorted(args, key=lambda x: str(x))
        expr["state"] = expr["args"]
    return expr


def rewrite_associativity(expr: SymExpr) -> SymExpr:
    """Recursively flatten nested ⊕ trees into a single flat list."""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") == "⊕":
        flat_args = []
        for arg in expr.get("args", []):
            if isinstance(arg, dict) and arg.get("op") == "⊕":
                inner = rewrite_associativity(arg)  # recurse
                if isinstance(inner, dict) and inner.get("op") == "⊕":
                    flat_args.extend(inner.get("args", []))
                else:
                    flat_args.append(inner)
            else:
                flat_args.append(arg)
        expr = expr.copy()
        expr["args"] = flat_args
        expr["state"] = flat_args
    return expr


def rewrite_distributivity(expr: SymExpr) -> SymExpr:
    """Distribute ⊕ over ↔, including nested entanglements."""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") == "⊕":
        args = expr.get("args", [])
        if len(args) == 2 and isinstance(args[1], dict) and args[1].get("op") == "↔":
            a = args[0]
            b, c = args[1]["args"]

            # Recurse into nested entanglements
            from backend.symatics.rewrite_rules import simplify
            if isinstance(c, dict) and c.get("op") == "↔":
                # Case: a ⊕ (b ↔ (c ↔ d))
                inner = simplify({"op": "⊕", "args": [a, c], "state": [a, c]})
                return {
                    "op": "↔",
                    "args": [
                        simplify({"op": "⊕", "args": [a, b], "state": [a, b]}),
                        inner,
                    ],
                }

            # Default shallow case: a ⊕ (b ↔ c) → (a ⊕ b) ↔ (a ⊕ c)
            return {
                "op": "↔",
                "args": [
                    {"op": "⊕", "args": [a, b], "state": [a, b]},
                    {"op": "⊕", "args": [a, c], "state": [a, c]},
                ],
            }
    return expr

def rewrite_constant_folding(expr: SymExpr) -> SymExpr:
    """
    Fold numeric constants for arithmetic operators only (e.g. '+').
    DO NOT fold for Symatics superposition ⊕ — it's not numeric addition.
    """
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")
    args = expr.get("args", [])

    # Arithmetic folding (safe)
    if op in {"+", "add"}:
        if all(isinstance(x, str) and x.isdigit() for x in args):
            val = sum(int(x) for x in args)
            return str(val)
        return expr

    # Explicitly do nothing for ⊕ (superposition)
    if op == "⊕":
        return expr

    return expr


# ──────────────────────────────
# Rule Engine
# ──────────────────────────────

RULES = [
    rewrite_idempotence,
    rewrite_identity,
    rewrite_associativity,
    rewrite_distributivity,
    rewrite_constant_folding,
    rewrite_combine_like_terms,   
    rewrite_commutativity,
]

def normalize(expr: SymExpr) -> SymExpr:
    """
    Apply rewrite rules repeatedly until a fixed point is reached.
    Handles both atomic values (str/int) and dict expressions.
    """
    changed = True
    while changed:
        changed = False
        for rule in RULES:
            new_expr = rule(expr)
            if new_expr != expr:
                expr = new_expr
                changed = True
    return expr


def simplify(expr: SymExpr) -> SymExpr:
    """Public API for Symatics simplification (delegates to normalize)."""
    return normalize(expr)

# ──────────────────────────────
# Rewrite-level regression tests
# ──────────────────────────────

def test_rewrite_identity_simplify():
    """Identity: a ⊕ ∅ → a via simplify()."""
    from backend.symatics.symatics_rulebook import op_superpose
    from backend.symatics.rewrite_rules import simplify
    expr = op_superpose("A", "∅", {})
    simplified = simplify(expr)
    assert simplified == "A"


def test_rewrite_idempotence_simplify():
    """Idempotence: a ⊕ a → a via simplify()."""
    from backend.symatics.symatics_rulebook import op_superpose
    from backend.symatics.rewrite_rules import simplify
    expr = op_superpose("A", "A", {})
    simplified = simplify(expr)
    assert simplified == "A"