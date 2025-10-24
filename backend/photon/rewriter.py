# backend/photon/rewriter.py
"""
Photon Rewriter
---------------
Normalization and equivalence checking for Photon expressions.
Uses axioms defined in photon/axioms.py.
"""

from backend.photon.axioms import AXIOMS
from backend.quant.qpy.compat_sympy import qundef
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr
import re

# Debug flag
DEBUG = True

# Define special SymPy functions
Grad = sp.Function("Grad")
Compose = sp.Function("Compose")  # for f ∘ g
LogicalAnd = sp.Function("And")
LogicalOr = sp.Function("Or")
LogicalNot = sp.Function("Not")


class GradPower(sp.Function):
    """Symbolic shorthand for higher-order gradients ∇ⁿ(expr)."""
    nargs = 2  # (expr, n)

    @classmethod
    def eval(cls, arg, n):
        n = int(n)
        if n == 1:
            return Grad(arg)
        if n == 0:
            return arg
        return None  # leave unevaluated for n>=2


# Mapping from Photon glyphs to Sympy-safe representations
GLYPH_MAP = {
    "⊕": "+",     # symbolic add
    "⊖": "-",     # symbolic subtract
    "⊗": "*",     # symbolic multiply
    "÷": "/",     # symbolic divide
    "↔": "Eq",    # equivalence → Eq(a,b)
    "≠": "Ne",    # inequality → Ne(a,b)
    "∧": "And",   # logical and
    "∨": "Or",    # logical or
    "¬": "Not",   # logical not
    "≥": ">=",    # greater or equal
    "≤": "<=",    # less or equal
    # Note: '∘' handled specially
}


def _dprint(*args):
    if DEBUG:
        print("[PhotonRewriter]", *args)


def _glyph_to_sympy(expr: str) -> str:
    """
    Convert a glyph expression into a Sympy-safe string.
    Handles Eq/Ne/Grad/Compose specially, with proper wrapping.
    Order of operations matters to avoid malformed outputs like Grad(g)(x).
    """
    expr = expr.strip()

    # 1) Handle equivalence and inequality
    if "↔" in expr:
        lhs, rhs = expr.split("↔", 1)
        return f"Eq({_glyph_to_sympy(lhs.strip())}, {_glyph_to_sympy(rhs.strip())})"
    if "≠" in expr:
        lhs, rhs = expr.split("≠", 1)
        return f"Ne({_glyph_to_sympy(lhs.strip())}, {_glyph_to_sympy(rhs.strip())})"

    # 2) Normalize (A ∘ B) → Compose(A,B)
    def _compose_repl(m):
        A = _glyph_to_sympy(m.group(1).strip())
        B = _glyph_to_sympy(m.group(2).strip())
        return f"Compose({A}, {B})"

    prev = None
    while prev != expr:
        prev = expr
        expr = re.sub(r"\(([^()]+?)\s*∘\s*([^)]+?)\)", _compose_repl, expr)

    # 3) Handle gradient with parentheses: ∇(...)
    if expr.startswith("∇(") and expr.endswith(")"):
        inner = expr[2:-1]
        return f"Grad({_glyph_to_sympy(inner.strip())})"

    # 4) Handle ∇f(args) → Grad(f(args))
    def _grad_fun_repl(m):
        name = m.group(1)
        args = m.group(2)
        return f"Grad({name}({args}))"

    expr = re.sub(r"∇\s*([A-Za-z_]\w*)\s*\(([^()]*)\)", _grad_fun_repl, expr)

    # 5) Bare ∇x → Grad(x)
    expr = re.sub(r"∇\s*([A-Za-z_]\w*)", r"Grad(\1)", expr)

    # 6) Translate remaining glyph operators
    out = expr
    for glyph, op in GLYPH_MAP.items():
        if glyph in ("↔", "≠"):
            continue
        out = out.replace(glyph, op)

    return out


def _product_rule(terms):
    """Expand gradient of product ∇(a*b*...)."""
    total = sp.Integer(0)
    for i, ti in enumerate(terms):
        others = terms[:i] + terms[i + 1 :]
        prod_others = sp.Mul(*others) if others else sp.Integer(1)
        total = total + Grad(ti) * prod_others
    return total


def _expand_gradient(expr, lazy=False, max_terms=3):
    """Gradient expansion rules (linearity, product rule, composition, nested functions, constants)."""
    if isinstance(expr, AppliedUndef) and expr.func == Grad:
        arg = expr.args[0]

        # Collapse higher-order derivatives
        if isinstance(arg, AppliedUndef) and arg.func == Grad:
            inner = arg.args[0]
            if isinstance(inner, GradPower):
                return GradPower(inner.args[0], int(inner.args[1]) + 1)
            else:
                return GradPower(inner, 2)

        # NEW: collapse Grad(GradPower(a,n)) directly
        if isinstance(arg, GradPower):
            return GradPower(arg.args[0], int(arg.args[1]) + 1)

        # Linearity: ∇(a + b) → ∇a + ∇b
        if isinstance(arg, sp.Add):
            return sp.Add(*[Grad(term) for term in arg.args])

        # Product rule — lazy mode avoids full expansion for large products
        if isinstance(arg, sp.Mul):
            if lazy and len(arg.args) > max_terms:
                return Grad(arg)
            return _product_rule(list(arg.args))

        # Explicit composition
        if isinstance(arg, AppliedUndef) and arg.func == Compose:
            f, g = arg.args
            return Compose(Grad(f), g) * Grad(g)

        # Chain rule: f(g(x))
        if isinstance(arg, sp.Function) and len(arg.args) == 1:
            inner = arg.args[0]
            f = arg.func
            return Compose(Grad(sp.Symbol(str(f))), inner) * Grad(inner)

        # Constants → 0
        if arg.is_Number:
            return sp.Integer(0)
        if arg.is_Symbol and getattr(arg, "is_constant", lambda: False)():
            return sp.Integer(0)

        return Grad(arg)

    return expr


class PhotonRewriter:
    def __init__(self, max_steps=200, max_size=5000, lazy_grad=False):
        self.axioms = AXIOMS
        self.local_dict = {
            "Eq": sp.Eq,
            "Ne": sp.Ne,
            "Grad": Grad,
            "GradPower": GradPower,
            "Compose": Compose,
            "And": LogicalAnd,
            "Or": LogicalOr,
            "Not": LogicalNot,
        }
        self.max_steps = max_steps
        self.max_size = max_size
        self.lazy_grad = lazy_grad

        # Pre-parse axioms once (cache)
        self._axioms_parsed = []
        for lhs, rhs, _ in self.axioms.values():
            try:
                lhs_sym = parse_expr(
                    _glyph_to_sympy(lhs), evaluate=False, local_dict=self.local_dict
                )
                rhs_sym = parse_expr(
                    _glyph_to_sympy(rhs), evaluate=False, local_dict=self.local_dict
                )
                self._axioms_parsed.append((lhs, rhs, lhs_sym, rhs_sym))
            except Exception:
                continue

    def normalize(self, expr: str):
        expr_std = _glyph_to_sympy(expr)
        expr_sym = parse_expr(expr_std, evaluate=False, local_dict=self.local_dict)

        _dprint("Initial parse:", expr, "=>", expr_std, "=>", expr_sym)

        seen = set()
        for step in range(self.max_steps):
            # safety: stop if expr grows too large
            if len(list(sp.preorder_traversal(expr_sym))) > self.max_size:
                _dprint(f"Aborting: expr too large at step {step}")
                break

            key = sp.srepr(expr_sym)
            if key in seen:
                _dprint("Cycle detected at step", step, "expr:", expr_sym)
                break
            seen.add(key)

            before = sp.srepr(expr_sym)

            # Expand gradients
            expr_sym = expr_sym.replace(
                lambda e: isinstance(e, AppliedUndef) and e.func == Grad,
                lambda e: _expand_gradient(e, lazy=self.lazy_grad),
            )

            if sp.srepr(expr_sym) != before:
                _dprint("Gradient expanded →", expr_sym)

            # Apply axioms
            for lhs, rhs, lhs_sym, rhs_sym in self._axioms_parsed:
                try:
                    new_expr = expr_sym.xreplace({lhs_sym: rhs_sym})
                    if new_expr != expr_sym:
                        _dprint(f"Axiom applied {lhs} → {rhs}: {expr_sym} → {new_expr}")
                        expr_sym = new_expr
                except Exception:
                    continue

        _dprint("Final normalized:", expr_sym)
        return expr_sym

    def equivalent(self, expr1: str, expr2: str) -> bool:
        n1 = self.normalize(expr1)
        n2 = self.normalize(expr2)

        _dprint("Compare:", expr1, "→", n1, "VS", expr2, "→", n2)

        if sp.srepr(n1) == sp.srepr(n2):
            return True

        try:
            if (n1 - n2).simplify() == 0:
                return True
        except Exception:
            pass

        return bool(getattr(n1, "equals", lambda *_: False)(n2)) or (str(n1) == str(n2))


# Singleton instance with defaults
rewriter = PhotonRewriter()