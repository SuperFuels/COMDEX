# File: backend/tests/test_symatics_theorems.py
"""
Symatics Theorems Test Suite (v0.3)
-----------------------------------
Tests axioms (A1–A8) of ⋈[φ] interference plus new irreducibility results.
Also integrates Lean ↔ CodexLang bridge to ensure consistency.
"""

import math
import pathlib
import pytest
import hypothesis.strategies as st
from hypothesis import given

import backend.symatics.rewriter as R
from backend.modules.lean.convert_lean_to_codexlang import convert_lean_to_codexlang

# ------------------------
# Shortcuts
# ------------------------
A = R.A()
B = R.B()
C = R.C()

THEOREM_RESULTS = []
BRIDGE_RESULTS = []


def _record_theorem(name: str, statement: str, status: bool):
    THEOREM_RESULTS.append((name, statement, status))
    assert status, f"{name} failed: {statement}"


# ------------------------
# Core theorems
# ------------------------

def test_self_identity_unique():
    stmt = "(A ⋈[φ] A) ↔ A ⇔ φ = 0"
    ok = (
        R.symatics_equiv(R.interf(0, A, A), A)
        and not R.symatics_equiv(R.interf(math.pi, A, A), A)
        and not R.symatics_equiv(R.interf(1.0, A, A), A)
    )
    _record_theorem("T1: Self-Identity", stmt, ok)


def test_self_annihilation_unique():
    stmt = "(A ⋈[φ] A) ↔ ⊥ ⇔ φ = π"
    ok = (
        R.normalize(R.interf(math.pi, A, A)) == R.Bot()
        and R.normalize(R.interf(0, A, A)) != R.Bot()
        and R.normalize(R.interf(1.0, A, A)) != R.Bot()
    )
    _record_theorem("T2: Self-Annihilation", stmt, ok)


def test_phase_cancellation():
    stmt = "A ⋈[φ] (A ⋈[−φ] B) ↔ B"
    φ = 1.23
    lhs = R.interf(φ, A, R.interf(-φ, A, B))
    ok = R.symatics_equiv(lhs, B)
    _record_theorem("T3: Phase-Cancellation", stmt, ok)


def test_associativity_normal_form():
    stmt = "((A ⋈[φ] B) ⋈[ψ] C) ↔ (A ⋈[φ+ψ] (B ⋈[ψ] C))"
    φ, ψ = 0.7, 1.1
    lhs = R.interf(ψ, R.interf(φ, A, B), C)
    rhs = R.interf(φ + ψ, A, R.interf(ψ, B, C))
    ok = R.symatics_structural_equiv(lhs, rhs)
    _record_theorem("T4: Associativity", stmt, ok)


def test_no_distributivity_nontrivial():
    stmt = "Distributivity fails for φ ∉ {0, π}"
    φ = 1.0
    lhs = R.interf(φ, A, R.interf(0.0, B, C))
    rhs = R.interf(0.0, R.interf(φ, A, B), R.interf(φ, A, C))
    ok = not R.symatics_equiv(R.normalize(lhs), R.normalize(rhs))
    _record_theorem("T5: No-Distributivity", stmt, ok)


def test_no_fixed_point_nontrivial():
    stmt = "X = A ⋈[φ] X has no solutions for φ ≠ 0,π"
    φ = 0.5
    X = C
    lhs = R.interf(φ, A, X)
    ok = R.normalize(lhs) != X
    _record_theorem("T6: No-Fixed-Point", stmt, ok)


def test_no_distrib_formal():
    stmt = "((A ⋈[φ] B) ∧ C) ≠ ((A ∧ C) ⋈[φ] (B ∧ C)) for φ ≠ 0,π"
    φ = 0.7
    lhs = R.interf(φ, R.interf(φ, A, B), C)
    rhs = R.interf(φ, R.interf(0, A, C), R.interf(0, B, C))
    ok = not R.symatics_equiv(R.normalize(lhs), R.normalize(rhs))
    _record_theorem("T7: Irreducibility", stmt, ok)


# ------------------------
# Property-based fuzz
# ------------------------

@given(st.integers(min_value=-6, max_value=6))
def test_idempotence_and_annihilation_unique(k):
    φ = k * (math.pi / 3)
    expr = R.interf(φ, A, A)
    norm = R.normalize(expr)
    if R.is_zero_phase(φ):
        assert norm == A
    elif R.is_pi_phase(φ):
        assert norm == R.Bot()
    else:
        assert norm != A
        assert norm != R.Bot()


# ------------------------
# Lean ↔ CodexLang Bridge validation
# ------------------------

def test_lean_axioms_bridge_consistency():
    """Load Lean axioms, convert, and check normalization passes."""
    lean_file = "backend/modules/lean/symatics_axioms.lean"
    results = convert_lean_to_codexlang(lean_file)

    for decl in results["parsed_declarations"]:
        nm = decl["name"]
        raw_logic = decl["logic_raw"]
        norm_logic = decl["logic"]

        status = norm_logic is not None and norm_logic != ""
        BRIDGE_RESULTS.append((nm, raw_logic, norm_logic, status))
        assert status, f"Lean→CodexLang conversion failed for {nm}"


# ------------------------
# Artifact export
# ------------------------

def pytest_sessionfinish(session, exitstatus):
    outdir = pathlib.Path("docs/rfc")
    outdir.mkdir(parents=True, exist_ok=True)

    # Theorem table
    with open(outdir / "theorems_results.md", "w") as f:
        f.write("# Symatics Theorems Results\n\n")
        f.write("| Theorem | Statement | Result |\n")
        f.write("|---------|-----------|--------|\n")
        for name, stmt, status in THEOREM_RESULTS:
            icon = "✅" if status else "❌"
            f.write(f"| {name} | `{stmt}` | {icon} |\n")

    # Bridge consistency table
    with open(outdir / "theorems_codexlang.md", "w") as f:
        f.write("# Symatics Lean ↔ CodexLang Bridge\n\n")
        f.write("| Name | Lean Logic | Normalized CodexLang | Result |\n")
        f.write("|------|------------|-----------------------|--------|\n")
        for nm, raw, norm, status in BRIDGE_RESULTS:
            icon = "✅" if status else "❌"
            f.write(f"| {nm} | `{raw}` | `{norm}` | {icon} |\n")

    print(f"\n📄 Theorem results written to {outdir/'theorems_results.md'}")
    print(f"📄 Lean↔CodexLang results written to {outdir/'theorems_codexlang.md'}\n")


if __name__ == "__main__":
    pytest.main([__file__, "-q"])