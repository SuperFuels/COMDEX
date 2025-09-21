# 📁 backend/tests/test_symatics_rulebook.py
import pytest

from backend.symatics.symatics_rulebook import (
    op_superpose,
    op_entangle,
    op_project,
    law_commutativity,
    law_associativity,
    law_idempotence,
    law_distributivity,
    law_projection,
    collapse_rule,
    check_all_laws,
)

# ──────────────────────────────
# Operator Tests
# ──────────────────────────────

def test_superpose_commutativity():
    a, b = "x", "y"
    assert law_commutativity("⊕", a, b)

def test_entangle_commutativity():
    a, b = "α", "β"
    assert law_commutativity("↔", a, b)

def test_associativity_superpose():
    a, b, c = "1", "2", "3"
    assert law_associativity("⊕", a, b, c)

def test_idempotence_superpose():
    a = "z"
    assert law_idempotence("⊕", a)

def test_distributivity_superpose_entangle():
    a, b, c = "p", "q", "r"
    assert law_distributivity(a, b, c)

def test_projection_law_simple():
    seq = [1, 2, 3]
    assert law_projection(seq, 1, 0)

def test_projection_out_of_bounds():
    seq = [1, 2, 3]
    # π(seq, 10) should fail gracefully
    result = op_project(seq, 10, {})
    assert result["value"] is None

def test_collapse_rule_on_superpose():
    expr = op_superpose("a", "b", {})
    collapsed = collapse_rule(expr)
    assert collapsed in {"a", "b"}

# ──────────────────────────────
# Meta: check_all_laws
# ──────────────────────────────

def test_check_all_laws_superpose():
    laws = check_all_laws("⊕", "u", "v", "w")
    assert "commutativity" in laws
    assert "associativity" in laws
    assert "idempotence" in laws
    assert "identity" in laws   # 🔑 new formal check
    assert "distributivity" in laws

def test_check_all_laws_projection():
    laws = check_all_laws("π", [1, 2, 3], 1, 0)
    assert "projection" in laws

# ──────────────────────────────
# Regression Tests (to lock in laws)
# ──────────────────────────────

def test_regression_associativity_superpose():
    """Regression: (a ⊕ b) ⊕ c == a ⊕ (b ⊕ c)."""
    a, b, c = "A", "B", "C"
    from backend.symatics.symatics_rulebook import _canonical, op_superpose
    left = op_superpose(op_superpose(a, b, {}), c, {})
    right = op_superpose(a, op_superpose(b, c, {}), {})
    assert _canonical(left) == _canonical(right)


def test_regression_identity_superpose():
    """Regression: a ⊕ ∅ = a."""
    a = "X"
    from backend.symatics.symatics_rulebook import _canonical, op_superpose
    expr = op_superpose(a, "∅", {})
    assert _canonical(expr) == _canonical(a)


def test_regression_idempotence_superpose():
    """Regression: a ⊕ a = a."""
    a = "Y"
    from backend.symatics.symatics_rulebook import _canonical, op_superpose
    expr = op_superpose(a, a, {})
    assert _canonical(expr) == _canonical(a)


def test_regression_distributivity_superpose_entangle():
    """Regression: a ⊕ (b ↔ c) == (a ⊕ b) ↔ (a ⊕ c)."""
    a, b, c = "P", "Q", "R"
    from backend.symatics.symatics_rulebook import _canonical, op_superpose, op_entangle
    left = op_superpose(a, op_entangle(b, c, {}), {})
    right = op_entangle(op_superpose(a, b, {}), op_superpose(a, c, {}), {})
    assert _canonical(left) == _canonical(right)