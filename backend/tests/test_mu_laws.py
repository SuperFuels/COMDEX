# tests/symatics/test_mu_laws.py
from backend.symatics.symatics_dispatcher import evaluate_symatics_expr

def test_mu_on_symbolic_is_3_of_3():
    r = evaluate_symatics_expr({"op":"μ","args":["X"]})
    assert r["law_check"]["summary"] == "3/3 passed"
    assert r["law_check"]["violations"] == []

def test_mu_equiv_nabla_on_superposition():
    sup = {"op":"⊕","args":["a","b"]}
    r = evaluate_symatics_expr({"op":"μ","args":[sup]})
    laws = r["law_check"]["laws"]
    assert laws["collapse_equivalence"] is True