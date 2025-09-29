# File: backend/modules/tests/test_operator_deprecations.py
import pytest


def test_entangle_stub_warns():
    from backend.symatics.operators.entangle import entangle_op

    with pytest.deprecated_call():
        result = entangle_op.impl("a", "b")

    # Ensure it actually returns something
    assert result is not None


def test_superpose_stub_warns():
    from backend.symatics.operators.superpose import superpose_op

    with pytest.deprecated_call():
        result = superpose_op.impl("a", "b")

    assert result is not None


def test_measure_stub_warns():
    from backend.symatics.operators.measure import measure_op

    with pytest.deprecated_call():
        result = measure_op.impl("a")

    assert result is not None