# File: backend/symatics/rewriter.py
"""
Symatics Rewriter (v1.0 - canonical-backed)
-------------------------------------------
Rewriter for Symatics interference algebra.

- Legacy classes (Atom, Bot, SymAdd, SymSub, Interf) are kept as thin wrappers
  that internally construct canonical AST (Sym/App).
- Canonical AST is defined in symatics/terms.py:
    * Var, Sym, App, Term
- normalize(), symatics_equiv(), etc. work transparently on both legacy + canonical.
- This allows old tests to pass while new code can move to canonical API.
"""

import math
import warnings
from typing import Optional, Union

from backend.symatics.terms import Var, Sym, App, Term

# -----------------
# Phase utilities
# -----------------

TAU = 2 * math.pi


def norm_phase(phi: float) -> float:
    """Normalize phase to (-π, π] with rounding for stability."""
    phi = phi % TAU
    if phi > math.pi:
        phi -= TAU
    return round(phi, 6)


def is_zero_phase(phi: float, tol: float = 1e-6) -> bool:
    return abs(norm_phase(phi)) < tol


def is_pi_phase(phi: float, tol: float = 1e-6) -> bool:
    return abs(abs(norm_phase(phi)) - math.pi) < tol


def _phi_sym(phi: float) -> Sym:
    """Stable string encoding for phase values as Sym."""
    return Sym(f"{norm_phase(phi):.6f}")


# -----------------
# Legacy wrappers (deprecated)
# -----------------

import warnings
from backend.symatics.terms import Sym

# Temporary compatibility shim
class Atom:
    def __new__(cls, name: str):
        warnings.warn(
            "Atom is deprecated; use Sym instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return Sym(name)

class Bot:
    def __new__(cls):
        warnings.warn("Bot is deprecated; use Sym('⊥') instead", DeprecationWarning, stacklevel=2)
        return Sym("⊥")


class SymAdd:
    def __new__(cls, left, right):
        warnings.warn("SymAdd is deprecated; use App(Sym('⊕'), ...) instead", DeprecationWarning, stacklevel=2)
        return App(Sym("⊕"), [to_canonical(left), to_canonical(right)])


class SymSub:
    def __new__(cls, left, right):
        warnings.warn("SymSub is deprecated; use App(Sym('⊖'), ...) instead", DeprecationWarning, stacklevel=2)
        return App(Sym("⊖"), [to_canonical(left), to_canonical(right)])


class Interf:
    def __new__(cls, phase: float, left, right):
        warnings.warn("Interf is deprecated; use App(Sym('⋈'), ...) instead", DeprecationWarning, stacklevel=2)
        return App(Sym("⋈"), [_phi_sym(phase),
                               to_canonical(left),
                               to_canonical(right)])


# Legacy type alias
Expr = Union[Atom, Bot, SymAdd, SymSub, Interf, Term]

# -----------------
# Canonical bridge
# -----------------


def to_canonical(expr: Expr) -> Term:
    """Convert legacy Expr -> canonical Term (noop if already canonical)."""
    if isinstance(expr, (Sym, Var, App)):
        return expr
    raise TypeError(f"Unsupported expression type: {expr}")


def from_canonical(term: Term) -> Expr:
    """Convert canonical Term -> legacy-style Expr (deprecated)."""
    if isinstance(term, Sym):
        if term.name == "⊥":
            return Bot()
        return Atom(term.name)
    if isinstance(term, Var):
        return Atom(term.name)
    if isinstance(term, App):
        if isinstance(term.head, Sym):
            op = term.head.name
            if op == "⊕":
                return SymAdd(from_canonical(term.args[0]), from_canonical(term.args[1]))
            if op == "⊖":
                return SymSub(from_canonical(term.args[0]), from_canonical(term.args[1]))
            if op == "⋈":
                φ = float(term.args[0].name) if isinstance(term.args[0], Sym) else 0.0
                return Interf(φ, from_canonical(term.args[1]), from_canonical(term.args[2]))
        return Atom(str(term))
    raise TypeError(f"Unsupported canonical term: {term}")


# -----------------
# Rewrite rules
# -----------------

def rewrite_once(expr: Term) -> Optional[Term]:
    """Single-step rewrite on canonical terms."""
    if not isinstance(expr, App):
        return None

    if isinstance(expr.head, Sym) and expr.head.name == "⋈":
        φ_sym, left, right = expr.args
        φ = float(φ_sym.name) if isinstance(φ_sym, Sym) else 0.0
        φ = norm_phase(φ)

        # A6 inv_phase: A ⋈[φ] (A ⋈[-φ] B) -> B
        if isinstance(right, App) and isinstance(right.head, Sym) and right.head.name == "⋈":
            inner_phase_sym, inner_left, inner_right = right.args
            inner_phase = float(inner_phase_sym.name) if isinstance(inner_phase_sym, Sym) else 0.0
            if inner_left == left and norm_phase(inner_phase) == norm_phase(-φ):
                return inner_right

        # A4 Neutrality: A ⋈[φ] ⊥ -> A
        if right == Sym("⊥"):
            return left

        # A2/A3 Self-interference
        if left == right:
            if is_zero_phase(φ):   # φ = 0 -> A
                return left
            if is_pi_phase(φ):     # φ = π -> ⊥
                return Sym("⊥")

        # A1 comm_phi: enforce ordering
        if isinstance(left, Sym) and isinstance(right, Sym):
            if left.name > right.name:
                return App(Sym("⋈"), [_phi_sym(-φ), right, left])

        # A5 assoc_phase
        if isinstance(left, App) and isinstance(left.head, Sym) and left.head.name == "⋈":
            φL_sym, a, b = left.args
            φL = float(φL_sym.name) if isinstance(φL_sym, Sym) else 0.0
            ψ = φ
            return App(Sym("⋈"), [
                _phi_sym(φL + ψ),
                a,
                App(Sym("⋈"), [_phi_sym(ψ), b, right]),
            ])

        # A7/A8 Phase fusion
        if is_zero_phase(φ):
            return App(Sym("⊕"), [left, right])
        if is_pi_phase(φ):
            return App(Sym("⊖"), [left, right])

        # Try children
        new_left = rewrite_once(left)
        if new_left is not None:
            return App(Sym("⋈"), [_phi_sym(φ), new_left, right])
        new_right = rewrite_once(right)
        if new_right is not None:
            return App(Sym("⋈"), [_phi_sym(φ), left, new_right])

    return None


# -----------------
# Normalization
# -----------------

def normalize(expr: Expr, max_steps: int = 200) -> Term:
    """Apply rewrite rules until fixpoint or max_steps reached."""
    term = to_canonical(expr)
    current = term
    for _ in range(max_steps):
        new = rewrite_once(current)
        if new is None:
            return current
        current = new
    raise RuntimeError("Rewrite did not converge")


# -----------------
# Equivalence
# -----------------

def symatics_structural_equiv(e1: Expr, e2: Expr) -> bool:
    return normalize(e1) == normalize(e2)


def symatics_equiv(e1: Expr, e2: Expr) -> bool:
    n1, n2 = normalize(e1), normalize(e2)
    if n1 == n2:
        if isinstance(n1, App) and isinstance(n1.head, Sym) and n1.head.name == "⋈":
            φ_sym = n1.args[0]
            φ = float(φ_sym.name) if isinstance(φ_sym, Sym) else 0.0
            return is_zero_phase(φ) or is_pi_phase(φ)
        return True
    return False


# -----------------
# Helpers
# -----------------

from backend.symatics.terms import Sym  # ensure imported
from backend.symatics.rewriter import Interf, norm_phase  # needed for interf()

def A(name="A") -> Sym:
    """Helper: create a Sym for symbol A."""
    return Sym(name)

def B(name="B") -> Sym:
    """Helper: create a Sym for symbol B."""
    return Sym(name)

def C(name="C") -> Sym:
    """Helper: create a Sym for symbol C."""
    return Sym(name)

def interf(φ, left, right):
    """Helper: construct interference node with normalized phase."""
    return Interf(norm_phase(φ), left, right)