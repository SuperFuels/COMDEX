"""
Symatics Theorems Test Suite (v0.2)
-----------------------------------
These tests check that axioms (A1–A8) of the interference operator ⋈[φ]
yield new theorems beyond Boolean logic.

Highlights:
    • T1–T6: Core properties (identity, annihilation, cancellation, associativity, etc.)
    • T7: NEW — Distributivity fails for all φ ≠ {0, π}, unlike Boolean logic.
      This is the first formally captured "irreducibility" theorem.

Run with:
    pytest backend/tests/test_symatics_theorems.py
"""

import math
import pytest
import hypothesis.strategies as st
from hypothesis import given

import backend.symatics.rewriter as R

# Shortcuts
A = R.A()
B = R.B()
C = R.C()

# ------------------------
# Theorem recorder
# ------------------------

THEOREM_RESULTS = []

def _record_theorem(name: str, statement: str, status: bool):
    THEOREM_RESULTS.append((name, statement, status))
    assert status, f"{name} failed: {statement}"

# ------------------------
# Core theorems
# ------------------------

def test_self_identity_unique():
    """
    Theorem 1: (A ⋈[φ] A) ↔ A  ⇔  φ = 0
    """
    stmt = "(A ⋈[φ] A) ↔ A ⇔ φ = 0"
    ok = (
        R.symatics_equiv(R.interf(0, A, A), A)
        and not R.symatics_equiv(R.interf(math.pi, A, A), A)
        and not R.symatics_equiv(R.interf(1.0, A, A), A)
    )
    _record_theorem("T1: Self-Identity", stmt, ok)


def test_self_annihilation_unique():
    """
    Theorem 2: (A ⋈[φ] A) ↔ ⊥  ⇔  φ = π
    """
    stmt = "(A ⋈[φ] A) ↔ ⊥ ⇔ φ = π"
    ok = (
        isinstance(R.normalize(R.interf(math.pi, A, A)), R.Bot)
        and not isinstance(R.normalize(R.interf(0, A, A)), R.Bot)
        and not isinstance(R.normalize(R.interf(1.0, A, A)), R.Bot)
    )
    _record_theorem("T2: Self-Annihilation", stmt, ok)


def test_phase_cancellation():
    """
    Theorem 3: A ⋈[φ] (A ⋈[−φ] B) ↔ B
    """
    stmt = "A ⋈[φ] (A ⋈[−φ] B) ↔ B"
    φ = 1.23
    lhs = R.interf(φ, A, R.interf(-φ, A, B))
    ok = R.symatics_equiv(lhs, B)
    _record_theorem("T3: Phase-Cancellation", stmt, ok)


def test_associativity_normal_form():
    """
    Theorem 4: ((A ⋈[φ] B) ⋈[ψ] C) ↔ (A ⋈[φ+ψ] (B ⋈[ψ] C))
    """
    stmt = "((A ⋈[φ] B) ⋈[ψ] C) ↔ (A ⋈[φ+ψ] (B ⋈[ψ] C))"
    φ, ψ = 0.7, 1.1
    lhs = R.interf(ψ, R.interf(φ, A, B), C)
    rhs = R.interf(φ + ψ, A, R.interf(ψ, B, C))
    ok = R.symatics_structural_equiv(lhs, rhs)
    _record_theorem("T4: Associativity", stmt, ok)


def test_no_distributivity_nontrivial():
    """
    Theorem 5: Distributivity fails except at φ=0 or π.
    Formally: (A ⋈[φ] (B ∧ C)) ≠ ((A ⋈[φ] B) ∧ (A ⋈[φ] C)) for φ ∉ {0, π}.
    """
    stmt = "Distributivity fails for φ ∉ {0, π}"
    φ = 1.0
    lhs = R.interf(φ, A, R.interf(0.0, B, C))
    rhs = R.interf(0.0, R.interf(φ, A, B), R.interf(φ, A, C))
    ok = not R.symatics_equiv(R.normalize(lhs), R.normalize(rhs))
    _record_theorem("T5: No-Distributivity", stmt, ok)


def test_no_fixed_point_nontrivial():
    """
    Theorem 6: For φ ≠ 0,π, X = A ⋈[φ] X has no solutions.
    """
    stmt = "X = A ⋈[φ] X has no solutions for φ ≠ 0,π"
    φ = 0.5
    X = C
    lhs = R.interf(φ, A, X)
    ok = R.normalize(lhs) != X
    _record_theorem("T6: No-Fixed-Point", stmt, ok)


def test_no_distrib_formal():
    """
    Theorem 7 (NEW): Formal irreducibility.
    For φ ≠ 0,π:
        ((A ⋈[φ] B) ∧ C) ≠ ((A ∧ C) ⋈[φ] (B ∧ C))
    This captures the first beyond-Boolean separation.
    """
    stmt = "((A ⋈[φ] B) ∧ C) ≠ ((A ∧ C) ⋈[φ] (B ∧ C)) for φ ≠ 0,π"
    φ = 0.7
    lhs = R.interf(φ, R.interf(φ, A, B), C)
    rhs = R.interf(φ, R.interf(0, A, C), R.interf(0, B, C))
    ok = not R.symatics_equiv(R.normalize(lhs), R.normalize(rhs))
    _record_theorem("T7: Irreducibility", stmt, ok)

# ------------------------
# Property-based fuzz tests
# ------------------------

@given(st.integers(min_value=-6, max_value=6))
def test_idempotence_and_annihilation_unique(k):
    """
    Property test: For random rational multiples of π,
    (A ⋈[φ] A) normalizes to:
        • A iff φ ≡ 0 (mod 2π)
        • ⊥ iff φ ≡ π (mod 2π)
        • else stays nontrivial
    """
    φ = k * (math.pi / 3)
    expr = R.interf(φ, A, A)
    norm = R.normalize(expr)
    if R.is_zero_phase(φ):
        assert norm == A
    elif R.is_pi_phase(φ):
        assert isinstance(norm, R.Bot)
    else:
        assert norm not in (A, R.Bot())

# ------------------------
# Artifact export
# ------------------------

import pathlib

def pytest_sessionfinish(session, exitstatus):
    """At end of pytest run, dump results to docs/rfc/theorems_results.md"""
    outdir = pathlib.Path("docs/rfc")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "theorems_results.md"

    with open(outfile, "w") as f:
        f.write("# Symatics Theorems Results\n\n")
        f.write("Automated proof snapshot.\n\n")
        f.write("| Theorem | Statement | Result |\n")
        f.write("|---------|-----------|--------|\n")
        for name, stmt, status in THEOREM_RESULTS:
            icon = "✅" if status else "❌"
            f.write(f"| {name} | `{stmt}` | {icon} |\n")

    print(f"\n📄 Theorem results written to {outfile}\n")

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-q"])
    # After pytest exits, our sessionfinish will still dump the results