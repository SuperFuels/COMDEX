# backend/modules/tests/test_operator_registry.py
import pytest

from backend.symatics.operators import OPS, Operator, apply_operator


def test_all_ops_are_operator_instances():
    """Every entry in OPS must be an Operator instance."""
    for symbol, op in OPS.items():
        assert isinstance(op, Operator), f"{symbol} is not an Operator"


@pytest.mark.parametrize("symbol,arity", [
    ("⊕", 2),   # superpose
    ("↔", 2),   # entangle
    ("μ", 1),   # measure
    ("π", 1),   # project
    ("⋈", 2),   # fuse
    ("↯", 1),   # damping
    ("⊖", 2),   # cancel
    ("⊗", 2),   # stub
    ("≡", 2),   # stub
    ("¬", 1),   # stub
])
def test_operator_arity(symbol, arity):
    """Operators should advertise correct arity."""
    assert OPS[symbol].arity == arity


def test_apply_operator_rejects_unknown():
    with pytest.raises(ValueError):
        apply_operator("??", "a", "b")


def test_apply_operator_rejects_wrong_arity():
    with pytest.raises(ValueError):
        apply_operator("⊕", "only-one-arg")


def test_stub_ops_dispatch():
    """Stub ops should return tuples that encode their call."""
    assert apply_operator("⊗", "a", "b") == ("⊗", ("a", "b"))
    assert apply_operator("≡", "x", "y") == ("≡", ("x", "y"))
    assert apply_operator("¬", "z") == ("¬", "z")