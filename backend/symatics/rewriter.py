"""
Symatics Rewriter (v0.8)
------------------------
Normalizes expressions built from the interference connective ⋈[φ].
- Enforces canonical right-associative form for associativity.
- Implements axioms (A1–A8) as rewrite rules.
- Provides two equivalence checks:
    • symatics_structural_equiv → purely structural (normalized tree equality)
    • symatics_equiv → truth-style (enforces φ ≡ 0 or π for equivalence)
"""

from dataclasses import dataclass
from typing import Union, Optional
import math

# -----------------
# Expression classes
# -----------------

@dataclass(frozen=True)
class Atom:
    name: str

@dataclass(frozen=True)
class Interf:
    phase: float
    left: "Expr"
    right: "Expr"

@dataclass(frozen=True)
class Bot:
    pass

@dataclass(frozen=True)
class SymAdd:
    """Constructive interference (A7): A ⊕ B"""
    left: "Expr"
    right: "Expr"

@dataclass(frozen=True)
class SymSub:
    """Destructive interference (A8): A ⊖ B"""
    left: "Expr"
    right: "Expr"

Expr = Union[Atom, Interf, Bot, SymAdd, SymSub]

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

# -----------------
# Rewriting rules
# -----------------

def rewrite_once(expr: Expr) -> Optional[Expr]:
    if isinstance(expr, Interf):
        φ = norm_phase(expr.phase)

        # A6 inv_phase: A ⋈[φ] (A ⋈[−φ] B) → B
        if isinstance(expr.right, Interf):
            inner = expr.right
            if inner.left == expr.left and norm_phase(inner.phase) == norm_phase(-φ):
                return inner.right

        # Recurse first
        new_left = rewrite_once(expr.left)
        if new_left is not None:
            return Interf(φ, new_left, expr.right)
        new_right = rewrite_once(expr.right)
        if new_right is not None:
            return Interf(φ, expr.left, new_right)

        # A4 Neutrality: A ⋈[φ] ⊥ → A
        if isinstance(expr.right, Bot):
            return expr.left

        # A2/A3 Self-interference
        if expr.left == expr.right:
            if is_zero_phase(φ):   # φ = 0 → A
                return expr.left
            if is_pi_phase(φ):    # φ = π → ⊥
                return Bot()

        # A1 comm_phi (canonical ordering of atoms)
        if isinstance(expr.left, Atom) and isinstance(expr.right, Atom):
            if expr.left.name > expr.right.name:
                return Interf(norm_phase(-φ), expr.right, expr.left)

        # A5 assoc_phase — force right-association
        if isinstance(expr.left, Interf):
            inner = expr.left
            φL = norm_phase(inner.phase)
            ψ = φ
            return Interf(
                norm_phase(φL + ψ),
                inner.left,
                Interf(ψ, inner.right, expr.right),
            )

        # A7/A8 Phase fusion rules
        if is_zero_phase(φ):
            return SymAdd(expr.left, expr.right)
        if is_pi_phase(φ):
            return SymSub(expr.left, expr.right)

    elif isinstance(expr, SymAdd):
        # recurse inside
        new_left = rewrite_once(expr.left)
        if new_left is not None:
            return SymAdd(new_left, expr.right)
        new_right = rewrite_once(expr.right)
        if new_right is not None:
            return SymAdd(expr.left, new_right)

    elif isinstance(expr, SymSub):
        # recurse inside
        new_left = rewrite_once(expr.left)
        if new_left is not None:
            return SymSub(new_left, expr.right)
        new_right = rewrite_once(expr.right)
        if new_right is not None:
            return SymSub(expr.left, new_right)

    return None

# -----------------
# Normalization
# -----------------

def normalize(expr: Expr, max_steps: int = 200) -> Expr:
    """Apply rewrite rules until fixpoint or max_steps reached."""
    current = expr
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
    """
    Equivalence by normalized structure only.
    Ignores semantic restrictions on φ — pure tree equality.
    """
    return normalize(e1) == normalize(e2)

def symatics_equiv(e1: Expr, e2: Expr) -> bool:
    """
    Truth-style equivalence:
      • Normalize both sides
      • Interf(⋈) forms are equivalent only if φ ≡ 0 or π
      • Otherwise require strict structural equality
    """
    n1, n2 = normalize(e1), normalize(e2)
    if n1 == n2:
        if isinstance(n1, Interf):
            return is_zero_phase(n1.phase) or is_pi_phase(n1.phase)
        return True
    return False

# -----------------
# Helpers
# -----------------

def A(name="A"): return Atom(name)
def B(name="B"): return Atom(name)
def C(name="C"): return Atom(name)
def interf(φ, left, right): return Interf(norm_phase(φ), left, right)