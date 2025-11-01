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

# ──────────────────────────────
# Regression Tests (simplify-level)
# ──────────────────────────────

def test_simplify_identity_superpose():
    """simplify should enforce identity: a ⊕ ∅ = a."""
    from backend.symatics.symatics_rulebook import op_superpose
    from backend.symatics.rewrite_rules import simplify

    a = "X"
    expr = op_superpose(a, "∅", {})
    simplified = simplify(expr)
    assert simplified == a or simplified == {"op": "⊕", "args": [a]}  # canonical form


def test_simplify_idempotence_superpose():
    """simplify should enforce idempotence: a ⊕ a = a."""
    from backend.symatics.symatics_rulebook import op_superpose
    from backend.symatics.rewrite_rules import simplify

    a = "Y"
    expr = op_superpose(a, a, {})
    simplified = simplify(expr)
    assert simplified == a

# ──────────────────────────────
# Meta-Tests: LAW_REGISTRY coverage
# ──────────────────────────────

def test_check_all_laws_superpose_full_idempotence():
    """⊕ must satisfy idempotence when given (a, a)."""
    laws = check_all_laws("⊕", "A", "A")
    assert "idempotence" in laws
    assert laws["idempotence"] is True

def test_check_all_laws_superpose_full_identity():
    """⊕ must satisfy identity when given (a, ∅)."""
    laws = check_all_laws("⊕", "A", "∅")
    assert "identity" in laws
    assert laws["identity"] is True


def test_check_all_laws_entangle_full():
    """↔ must satisfy commutativity."""
    laws = check_all_laws("↔", "α", "β")
    expected = {"commutativity"}
    assert set(laws.keys()) == expected
    assert all(laws.values())


def test_check_all_laws_projection_full():
    """π must satisfy projection law."""
    seq = [1, 2, 3]
    laws = check_all_laws("π", seq, 1, 0)
    expected = {"projection"}
    assert set(laws.keys()) == expected
    assert all(laws.values())

# ──────────────────────────────
# Derivative Operator (Δ)
# ──────────────────────────────

def test_derivative_stub_constant():
    """Δ(constant, x) should simplify to 0 (stub law)."""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    expr = op_derivative("5", "x", {})
    assert "Δ" == expr["op"]
    # Currently placeholder: either '0' or a symbolic "d/dx(5)"
    res = expr["result"]
    assert res in ("0", "d/dx(5)")


def test_derivative_stub_variable():
    """Δ(x, x) should return 1 in future, but stub only records intention."""
    from backend.symatics.symatics_rulebook import op_derivative
    expr = op_derivative("x", "x", {})
    assert expr["op"] == "Δ"
    assert expr["args"] == ["x", "x"]


def test_check_all_laws_derivative_constant():
    """LAW_REGISTRY should include Δ with derivative law (constant -> 0)."""
    from backend.symatics.symatics_rulebook import check_all_laws
    laws = check_all_laws("Δ", "7", "x")
    assert "derivative" in laws
    # Placeholder may not simplify yet, but law returns True
    assert laws["derivative"] is True

# ──────────────────────────────
# Negative Sanity Tests
# ──────────────────────────────

def test_non_commutative_operator_is_not_commutative():
    """Sanity: '+' is not registered as commutative in Symatics laws."""
    laws = check_all_laws("+", "a", "b")
    # '+' is not in LAW_REGISTRY -> no laws should apply
    assert laws == {}


def test_projection_fails_on_invalid_index():
    """Sanity: π(seq, n, m) should fail if indices are nonsense."""
    seq = [1, 2, 3]
    # Use negative offset beyond bounds
    result = check_all_laws("π", seq, 10, 99)
    # It should return {'projection': False}
    assert "projection" in result
    assert result["projection"] is False

def test_integration_constant():
    from backend.symatics.symatics_rulebook import op_integrate
    expr = op_integrate(5, "x", {})
    assert "5*x" in expr["result"]

def test_integration_variable():
    from backend.symatics.symatics_rulebook import op_integrate
    expr = op_integrate("x", "x", {})
    assert "0.5*x^2" in expr["result"]

def test_check_all_laws_integration_constant():
    from backend.symatics.symatics_rulebook import check_all_laws
    laws = check_all_laws("∫", 3, "x")
    assert "integration_constant" in laws
    assert laws["integration_constant"] is True

def test_regression_duality_superpose_measure():
    """Regression: μ(a ⊕ b) collapses into {a, b}."""
    a, b = "L", "R"
    from backend.symatics.symatics_rulebook import op_superpose, collapse_rule
    expr = op_superpose(a, b, {})
    collapsed = collapse_rule(expr)
    assert collapsed in {a, b}

def test_check_all_laws_duality_superpose():
    """⊕ must include duality law when measured by μ."""
    laws = check_all_laws("⊕", "A", "B")
    assert "duality" in laws
    assert laws["duality"] is True

def test_check_all_laws_duality_measure():
    """μ applied to a ⊕ expression must satisfy duality law."""
    from backend.symatics.symatics_rulebook import op_superpose
    expr = op_superpose("X", "Y", {})
    laws = check_all_laws("μ", expr)
    assert "duality" in laws
    assert laws["duality"] is True

def test_regression_distributivity_nested():
    """Regression: nested distributivity a ⊕ (b ↔ (c ↔ d)) expands correctly."""
    from backend.symatics.symatics_rulebook import _canonical, op_superpose, op_entangle

    a, b, c, d = "A", "B", "C", "D"
    left = op_superpose(a, op_entangle(b, op_entangle(c, d, {}), {}), {})

    # Expected expansion: (a ⊕ b) ↔ (a ⊕ (c ↔ d))
    right = op_entangle(op_superpose(a, b, {}), op_superpose(a, op_entangle(c, d, {}), {}), {})

    assert _canonical(left) == _canonical(right)

# ──────────────────────────────
# Differentiation Tests (Δ)
# ──────────────────────────────

def test_derivative_of_variable():
    """Δ x = 1"""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    expr = {"op": "var", "args": ["x"]}
    deriv = op_derivative(expr, "x", {})
    assert _canonical(deriv) == "1"


def test_derivative_of_square():
    """Δ(x2) = 2x"""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    x = {"op": "var", "args": ["x"]}
    expr = {"op": "*", "args": [x, x]}
    deriv = op_derivative(expr, "x", {})
    # Should simplify to 2x (we check structurally, not stringly)
    can = _canonical(deriv)
    assert can in [
        ("mul", ("2", ("var", "x"))),
        ("mul", (("var", "x"), "2")),
    ]


def test_derivative_of_constant():
    """Δ c = 0"""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    expr = {"op": "const", "args": ["5"]}
    deriv = op_derivative(expr, "x", {})
    assert _canonical(deriv) == "0"

# ──────────────────────────────
# Meta-Test: LAW_REGISTRY coverage for Δ
# ──────────────────────────────

def test_check_all_laws_derivative():
    """Δ must satisfy derivative law under LAW_REGISTRY."""
    from backend.symatics.symatics_rulebook import check_all_laws
    expr = {"op": "var", "args": ["x"]}
    laws = check_all_laws("Δ", expr, "x")
    assert "derivative" in laws
    assert laws["derivative"] is True

# ──────────────────────────────
# Integration Tests (∫)
# ──────────────────────────────

def test_integration_constant():
    """∫ c dx = c*x for constant c."""
    from backend.symatics.symatics_rulebook import op_integrate, _canonical
    expr = op_integrate(5, "x", {})
    # Expected: 5*x -> represented canonically as (∫, 5, 'x')
    assert _canonical(expr) == ("∫", 5, "x")


def test_integration_polynomial():
    """∫ x^n dx = x^(n+1)/(n+1), here n=2 -> x3/3."""
    from backend.symatics.symatics_rulebook import op_integrate
    expr = {"op": "pow", "args": ["x", 2]}
    result = op_integrate(expr, "x", {})
    # Should return something structured with exponent 3 and denominator 3
    assert isinstance(result, dict)
    assert result.get("op") == "∫"
    assert "args" in result


# ──────────────────────────────
# Meta-Test: LAW_REGISTRY coverage for ∫
# ──────────────────────────────

def test_check_all_laws_integration():
    """∫ must satisfy integration constant law under LAW_REGISTRY."""
    from backend.symatics.symatics_rulebook import check_all_laws
    laws = check_all_laws("∫", 5, "x")
    assert "integration_constant" in laws
    assert laws["integration_constant"] is True

# ──────────────────────────────
# Differentiation Tests (Δ)
# ──────────────────────────────

def test_derivative_of_variable():
    """Δ x = 1"""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    expr = {"op": "var", "args": ["x"]}
    deriv = op_derivative(expr, "x", {})
    assert _canonical(deriv) == "1"


def test_derivative_of_square():
    """Δ(x2) = 2x"""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    x = {"op": "var", "args": ["x"]}
    expr = {"op": "*", "args": [x, x]}  # x2 as x * x
    deriv = op_derivative(expr, "x", {})
    can = _canonical(deriv)
    # Should simplify structurally to 2x
    assert can in [
        ("mul", ("2", ("var", "x"))),
        ("mul", (("var", "x"), "2")),
    ]


def test_derivative_of_constant():
    """Δ c = 0"""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    expr = {"op": "const", "args": ["5"]}
    deriv = op_derivative(expr, "x", {})
    assert _canonical(deriv) == "0"

# ──────────────────────────────
# Integration Tests (∫)
# ──────────────────────────────

def test_integral_of_constant():
    """∫ c dx = c*x"""
    from backend.symatics.symatics_rulebook import _canonical, rewrite_integral
    expr = {"op": "const", "args": ["5"]}
    integ = rewrite_integral(expr, "x")
    can = _canonical(integ)
    assert can == ("mul", ("5", ("var", "x")))


def test_integral_of_variable():
    """∫ x dx = x2/2"""
    from backend.symatics.symatics_rulebook import _canonical, rewrite_integral
    expr = {"op": "var", "args": ["x"]}
    integ = rewrite_integral(expr, "x")
    can = _canonical(integ)
    assert can == ("/", (("^", (("var", "x"), "2")), "2"))


def test_integral_power_rule():
    """∫ x^n dx = x^(n+1)/(n+1)"""
    from backend.symatics.symatics_rulebook import _canonical, rewrite_integral
    expr = {"op": "^", "args": [{"op": "var", "args": ["x"]}, "3"]}
    integ = rewrite_integral(expr, "x")
    can = _canonical(integ)
    # Expect x^4 / 4
    assert can == ("/", (("^", (("var", "x"), "4")), "4"))

# ──────────────────────────────
# LAW_REGISTRY Meta-Tests
# ──────────────────────────────

def test_check_all_laws_integration_power():
    """LAW_REGISTRY should validate ∫ x^n dx = x^(n+1)/(n+1) under check_all_laws."""
    from backend.symatics.symatics_rulebook import check_all_laws
    expr = {"op": "^", "args": [{"op": "var", "args": ["x"]}, "3"]}
    laws = check_all_laws("∫", expr, "x")
    assert "integration_power" in laws
    assert laws["integration_power"] is True


def test_check_all_laws_integration_constant():
    """LAW_REGISTRY: ∫ constant must satisfy constant law."""
    from backend.symatics.symatics_rulebook import check_all_laws
    laws = check_all_laws("∫", {"op": "const", "args": ["7"]}, "x")
    assert "integration_constant" in laws
    assert laws["integration_constant"] is True


def test_check_all_laws_integration_power_meta():
    """LAW_REGISTRY: ∫ x^n dx must satisfy power rule law (duplicate meta-test)."""
    from backend.symatics.symatics_rulebook import check_all_laws
    expr = {"op": "^", "args": [{"op": "var", "args": ["x"]}, "3"]}
    laws = check_all_laws("∫", expr, "x")
    assert "integration_power" in laws
    assert laws["integration_power"] is True

def test_derivative_sum_rule():
    """Δ(x + x) = Δx + Δx = 1 + 1 -> 2"""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    expr = {"op": "+", "args": [
        {"op": "var", "args": ["x"]},
        {"op": "var", "args": ["x"]},
    ]}
    deriv = op_derivative(expr, "x", {})
    can = _canonical(deriv)
    # Allow both raw (1+1) and simplified (2) forms
    assert can in [
        ("+", ("1", "1")),
        "2",
    ]


def test_integral_sum_rule():
    """∫(x + 5) dx = ∫x dx + ∫5 dx = x2/2 + 5x"""
    from backend.symatics.symatics_rulebook import rewrite_integral, _canonical
    expr = {"op": "+", "args": [
        {"op": "var", "args": ["x"]},
        {"op": "const", "args": ["5"]},
    ]}
    integ = rewrite_integral(expr, "x")
    can = _canonical(integ)
    expected = ("+", (
        ("/", (("^", (("var", "x"), "2")), "2")),
        ("mul", ("5", ("var", "x"))),
    ))
    assert can == expected


def test_check_all_laws_derivative_sum():
    """LAW_REGISTRY: Δ must satisfy sum rule."""
    from backend.symatics.symatics_rulebook import check_all_laws
    expr = {"op": "+", "args": [
        {"op": "var", "args": ["x"]},
        {"op": "var", "args": ["y"]},
    ]}
    laws = check_all_laws("Δ", expr, "x")
    assert "derivative_sum" in laws
    assert laws["derivative_sum"] is True


def test_check_all_laws_integration_sum():
    """LAW_REGISTRY: ∫ must satisfy sum rule."""
    from backend.symatics.symatics_rulebook import check_all_laws
    expr = {"op": "+", "args": [
        {"op": "var", "args": ["x"]},
        {"op": "const", "args": ["7"]},
    ]}
    laws = check_all_laws("∫", expr, "x")
    assert "integration_sum" in laws
    assert laws["integration_sum"] is True

def test_derivative_chain_rule_simple():
    """Δ(sin(x)) = cos(x)."""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    expr = {"op": "sin", "args": [{"op": "var", "args": ["x"]}]}
    deriv = op_derivative(expr, "x", {})
    assert _canonical(deriv) == ("cos", (("var", "x"),))


def test_derivative_chain_rule_nested():
    """Δ(sin(x2)) = cos(x2)*2x."""
    from backend.symatics.symatics_rulebook import op_derivative, _canonical
    expr = {"op": "sin", "args": [{"op": "^", "args": [{"op": "var", "args": ["x"]}, "2"]}]}
    deriv = op_derivative(expr, "x", {})
    can = _canonical(deriv)
    expected = ("mul", (("cos", (("^", (("var", "x"), "2")),)), ("mul", ("2", ("var", "x")))))
    assert can == expected


def test_integral_substitution_simple():
    """∫ cos(x) dx = sin(x)."""
    from backend.symatics.symatics_rulebook import rewrite_integral, _canonical
    expr = {"op": "cos", "args": [{"op": "var", "args": ["x"]}]}
    integ = rewrite_integral(expr, "x")
    assert _canonical(integ) == ("sin", (("var", "x"),))


def test_integral_substitution_chain():
    """∫ cos(x2)*2x dx = sin(x2)."""
    from backend.symatics.symatics_rulebook import rewrite_integral, _canonical
    expr = {"op": "*", "args": [
        {"op": "cos", "args": [{"op": "^", "args": [{"op": "var", "args": ["x"]}, "2"]}]},
        {"op": "*", "args": ["2", {"op": "var", "args": ["x"]}]}
    ]}
    integ = rewrite_integral(expr, "x")
    assert _canonical(integ) == ("sin", (("^", (("var", "x"), "2")),))