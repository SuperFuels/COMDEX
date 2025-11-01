import pytest
from backend.symatics.symatics_rulebook import _canonical

# ──────────────────────────────
# Canonical Regression Tests
# ──────────────────────────────

def test_damping_superpose_distribution():
    expr = {"op": "↯⊕", "args": ["ψ1", "ψ2", 0.1]}
    canon = _canonical(expr)
    assert canon == (
        "⊕",
        (
            ("↯", ("ψ1", 0.1)),
            ("↯", ("ψ2", 0.1)),
        ),
    )

def test_projection_collapse_numeric_index():
    expr = {"op": "πμ", "args": [[[1, 2], [3, 4]], 0]}
    canon = _canonical(expr)
    # index must stay as int (0), not "0"
    assert canon == (
        "πμ",
        (
            (("1", "2"), ("3", "4")),
            0,
        ),
    )

@pytest.mark.parametrize("expr,expected", [
    # raw string distribution form
    ("(ψ1 ⊕ ψ2)*e^(-0.1*t)", ("⊕", (("↯", ("ψ1", "e^(-0.1*t)")), ("↯", ("ψ2", "e^(-0.1*t)"))))),
    # raw πμ string form
    ("πμ([[1,2],[3,4]],0)", ("πμ", ("πμ([[1,2],[3,4]],0)",))),
])
def test_string_forms(expr, expected):
    canon = _canonical(expr)
    assert canon == expected