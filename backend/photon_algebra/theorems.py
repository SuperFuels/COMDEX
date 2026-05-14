# -*- coding: utf-8 -*-
"""
Photon Calculus - Derived Theorems (T8-T15)
-------------------------------------------

This module defines *theorem checkers* in the repo’s style:

    theorem_Ti(...) returns True  iff  normalize(LHS) == normalize(RHS)

Important:
- These are PA-core equivalences under the **directed normalizer**.
- Runtime behaviors (sampling collapse with SQI, numeric scoring, etc.) are *not*
  part of the rewriter’s proof story and MUST NOT be relied on here.

Theorems:

- T8: Distributivity (⊗ over ⊕) — expansion direction used by normalize()
- T9: Double negation stability
- T10: Entanglement distributivity (↔ over ⊕) — if enabled in rewrite table
- T11: Collapse consistency (symbolic) — ∇ is treated structurally in PA-core
- T12: Projection fidelity (symbolic) — ★ is treated structurally in PA-core
- T13: Absorption
- T14: Dual distributivity (factoring) — intentionally NOT a PA-core theorem
      (design constraint: no factoring rule in ⊕ branch to avoid ping-pong)
- T15: Falsification (cancellation identity)
"""

from backend.photon_algebra import core, rewriter


# -------------------------
# Theorems (PA-core NF equalities)
# -------------------------
def theorem_T8(a, b, c) -> bool:
    """T8: Distributivity (expansion) - a ⊗ (b ⊕ c) == (a ⊗ b) ⊕ (a ⊗ c)."""
    lhs = core.fuse(a, core.superpose(b, c))
    rhs = core.superpose(core.fuse(a, b), core.fuse(a, c))
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T9(a) -> bool:
    """T9: Double negation - ¬(¬a) == a."""
    lhs = core.negate(core.negate(a))
    rhs = a
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T10(a, b, c) -> bool:
    """T10: Entanglement distributivity - (a↔b) ⊕ (a↔c) == a↔(b⊕c)."""
    lhs = core.superpose(core.entangle(a, b), core.entangle(a, c))
    rhs = core.entangle(a, core.superpose(b, c))
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T11(a) -> bool:
    """
    T11: Collapse consistency (symbolic, PA-core)

    In PA-core, collapse is represented structurally as {"op":"∇","state":...}.
    The rewriter may normalize the child, but does NOT perform sampling.

    Therefore we only claim structural consistency around normalization:
        ∇(NF(a)) == NF(∇(a))
    """
    lhs = core.collapse(rewriter.normalize(a), sqi=None)
    rhs = rewriter.normalize(core.collapse(a, sqi=None))
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T12(a, b) -> bool:
    """
    T12: Projection fidelity (symbolic, PA-core)

    In PA-core, ★ is structural: {"op":"★","state":...}.
    Any numeric meaning / SQI scoring is runtime-only.

    The PA-core rewrite rule (if present) is:
        ★(a↔b)  ==  (★a) ⊕ (★b)
    """
    lhs = core.project(core.entangle(a, b), sqi=None)
    rhs = core.superpose(core.project(a, sqi=None), core.project(b, sqi=None))
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T13(a, b) -> bool:
    """T13: Absorption - a ⊕ (a ⊗ b) == a."""
    lhs = core.superpose(a, core.fuse(a, b))
    rhs = a
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T14(a, b, c) -> bool:
    """
    T14: Dual distributivity (factoring) — intentionally NOT a PA-core theorem.

    This function returns True iff the equivalence happens to hold under the
    current directed normalizer, but DO NOT treat it as guaranteed.

    Design constraint:
        a ⊕ (b ⊗ c)  ↛  (a ⊕ b) ⊗ (a ⊕ c)

    We keep this here as a *negative theorem / guardrail* so callers/tests can
    assert it is NOT relied upon.
    """
    lhs = core.superpose(a, core.fuse(b, c))
    rhs = core.fuse(core.superpose(a, b), core.superpose(a, c))
    return rewriter.normalize(lhs) == rewriter.normalize(rhs)


def theorem_T15(a) -> bool:
    """T15: Falsification - a ⊖ ∅ == a and ∅ ⊖ a == a (as implemented)."""
    lhs1 = core.cancel(a, core.EMPTY)
    rhs1 = a
    lhs2 = core.cancel(core.EMPTY, a)
    rhs2 = a
    return (rewriter.normalize(lhs1) == rewriter.normalize(rhs1)) and (
        rewriter.normalize(lhs2) == rewriter.normalize(rhs2)
    )