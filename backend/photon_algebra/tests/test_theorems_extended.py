# -*- coding: utf-8 -*-
"""
Photon Calculus — Derived Theorems (T8–T12)
-------------------------------------------
Extends Photon Algebra axioms (P1–P8) with derived theorems:

- T8: Distributivity of superposition
- T9: Double negation stability
- T10: Entanglement distributivity
- T11: Collapse consistency
- T12: Projection fidelity
"""

from backend.photon_algebra import core, rewriter


def _norm(x):
    """Helper: normalize expressions consistently."""
    return rewriter.normalize(x)


# -------------------------
# Theorems (verification)
# -------------------------

def theorem_T8(a, b, c):
    """T8: Distributivity — a ⊗ (b ⊕ c) == (a ⊗ b) ⊕ (a ⊗ c)."""
    lhs = core.fuse(a, core.superpose(b, c))
    rhs = core.superpose(core.fuse(a, b), core.fuse(a, c))
    return _norm(lhs) == _norm(rhs)


def theorem_T9(a):
    """T9: Double negation — ¬(¬a) == a."""
    lhs = core.negate(core.negate(a))
    rhs = a
    return _norm(lhs) == _norm(rhs)


def theorem_T10(a, b, c):
    """T10: Entanglement distributivity — (a↔b) ⊕ (a↔c) == a↔(b⊕c)."""
    lhs = core.superpose(core.entangle(a, b), core.entangle(a, c))
    rhs = core.entangle(a, core.superpose(b, c))
    return _norm(lhs) == _norm(rhs)


def theorem_T11(a):
    """T11: Collapse consistency — ∇(a ⊕ ∅) == ∇(a)."""
    lhs = core.collapse(core.superpose(a, core.EMPTY))   # symbolic collapse
    rhs = core.collapse(a)                              # symbolic collapse
    return _norm(lhs) == _norm(rhs)


def theorem_T12(a, b):
    """T12: Projection fidelity — ★(a↔b) == ★(a) ⊕ ★(b)."""
    lhs = core.project(core.entangle(a, b))  # symbolic project
    rhs = core.superpose(core.project(a), core.project(b))
    return _norm(lhs) == _norm(rhs)