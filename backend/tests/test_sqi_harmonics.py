# backend/tests/test_sqi_harmonics.py
from backend.modules.sqi.sqi_harmonics import suggest_harmonics, apply_dependency_patch

def _container():
    return {
        "symbolic_logic": [
            {"name":"add_comm", "logic":"a+b=b+a", "depends_on":[]},
            {"name":"mul_assoc","logic":"(ab)c=a(bc)", "depends_on":[]},
            {"name":"zero_add", "logic":"0+n=n", "depends_on":[]},
        ]
    }

def test_suggest_harmonics_basic():
    c = _container()
    suggs = suggest_harmonics(c, "add_commutative", top_k=2)
    assert suggs and suggs[0][0] == "add_comm"

def test_apply_dependency_patch():
    c = _container()
    ok = apply_dependency_patch(c, "mul_assoc", ["add_comm","zero_add"])
    assert ok
    deps = next(e for e in c["symbolic_logic"] if e["name"]=="mul_assoc")["depends_on"]
    assert "add_comm" in deps and "zero_add" in deps