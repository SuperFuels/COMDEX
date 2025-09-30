# -*- coding: utf-8 -*-
"""
Photon Calculus — Derived Theorems (T8–T15)
-------------------------------------------
Extends Photon Algebra axioms (P1–P8) with derived theorems:

- T8: Distributivity of superposition
- T9: Double negation stability
- T10: Entanglement distributivity
- T11: Collapse consistency
- T12: Projection fidelity
- T13: Absorption
- T14: Dual Distributivity
- T15: Falsification
"""

from backend.photon_algebra import core, rewriter


# -------------------------
# Theorems
# -------------------------
def theorem_T8(a, b, c):
    """T8: Distributivity — a ⊗ (b ⊕ c) == (a ⊗ b) ⊕ (a ⊗ c)."""
    lhs = core.fuse(a, core.superpose(b, c))
    rhs = core.superpose(core.fuse(a, b), core.fuse(a, c))
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T9(a):
    """T9: Double negation — ¬(¬a) == a."""
    lhs = core.negate(core.negate(a))
    rhs = a
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T10(a, b, c):
    """T10: Entanglement distributivity — (a↔b) ⊕ (a↔c) == a↔(b⊕c)."""
    lhs = core.superpose(core.entangle(a, b), core.entangle(a, c))
    rhs = core.entangle(a, core.superpose(b, c))
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T11(a):
    """T11: Collapse consistency — ∇(a ⊕ ∅) == ∇(a) == a."""
    lhs = core.collapse(core.superpose(a, core.EMPTY), sqi={str(a): 1.0})
    rhs = core.collapse(a, sqi={str(a): 1.0})
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T12(a, b):
    """T12: Projection fidelity — ★(a↔b) == ★(a) ⊕ ★(b)."""
    lhs = core.project(core.entangle(a, b), sqi={str(a): 1.0, str(b): 1.0})
    rhs = core.superpose(core.project(a, sqi={str(a): 1.0}),
                         core.project(b, sqi={str(b): 1.0}))
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T13(a, b):
    """T13: Absorption — a ⊕ (a ⊗ b) == a."""
    lhs = core.superpose(a, core.fuse(a, b))
    rhs = a
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T14(a, b, c):
    """T14: Dual Distributivity — a ⊕ (b ⊗ c) == (a ⊕ b) ⊗ (a ⊕ c)."""
    lhs = core.superpose(a, core.fuse(b, c))
    rhs = core.fuse(core.superpose(a, b), core.superpose(a, c))
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T15(a):
    """T15: Falsification — a ⊖ ∅ == a."""
    lhs = core.cancel(a, core.EMPTY)
    rhs = a
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)