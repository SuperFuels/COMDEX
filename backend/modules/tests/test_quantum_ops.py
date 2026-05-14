# File: backend/tests/test_quantum_ops.py
"""
Quantum Ops Unification Tests
-----------------------------
Validates the unified quantum operators exposed via backend.symatics.quantum_ops:
  * superpose (⊕)
  * entangle (↔)
  * measure  (μ)
  * measurement_noisy (ε) [optional until implemented]
and their exposure through INSTRUCTION_REGISTRY.

These tests check:
  - registry wiring (ops are present and callable)
  - basic shape/contract of op outputs
  - simple algebraic properties that don't depend on internal simplifiers
  - measurement collapse on superpositions
"""

import pytest

# If the module isn't present yet, skip cleanly
quantum = pytest.importorskip("backend.symatics.quantum_ops")

# aliases
superpose = quantum.superpose
entangle = quantum.entangle
measure = quantum.measure
measurement_noisy = getattr(quantum, "measurement_noisy", None)
INSTRUCTION_REGISTRY = quantum.INSTRUCTION_REGISTRY


def _is_dict_with_op(d, op):
    return isinstance(d, dict) and d.get("op") == op


def _args(d):
    return d.get("args", []) if isinstance(d, dict) else []


# -------------------------
# Registry wiring / presence
# -------------------------

def test_registry_has_expected_ops():
    assert "⊕" in INSTRUCTION_REGISTRY
    assert "↔" in INSTRUCTION_REGISTRY
    assert "μ" in INSTRUCTION_REGISTRY
    if measurement_noisy:
        assert "ε" in INSTRUCTION_REGISTRY

    assert callable(INSTRUCTION_REGISTRY["⊕"])
    assert callable(INSTRUCTION_REGISTRY["↔"])
    assert callable(INSTRUCTION_REGISTRY["μ"])
    if measurement_noisy:
        assert callable(INSTRUCTION_REGISTRY["ε"])


def test_registry_callables_return_expected_ops():
    a, b = "A", "B"
    sup = INSTRUCTION_REGISTRY["⊕"](a, b)
    ent = INSTRUCTION_REGISTRY["↔"](a, b)
    meas = INSTRUCTION_REGISTRY["μ"](a)

    assert _is_dict_with_op(sup, "⊕")
    assert _is_dict_with_op(ent, "↔")
    assert _is_dict_with_op(meas, "μ")

    if measurement_noisy:
        noisy = INSTRUCTION_REGISTRY["ε"](a, 0.2)
        assert _is_dict_with_op(noisy, "ε")


# -------------------------
# Superpose (⊕)
# -------------------------

def test_superpose_shape_and_args():
    a, b = "ψA", "ψB"
    out = superpose(a, b)
    assert _is_dict_with_op(out, "⊕")
    args = _args(out)
    assert len(args) == 2
    assert args[0] == a and args[1] == b


def test_superpose_commutativity_by_multiset():
    a, b = "ψ1", "ψ2"
    ab = superpose(a, b)
    ba = superpose(b, a)
    assert _is_dict_with_op(ab, "⊕")
    assert _is_dict_with_op(ba, "⊕")
    # Compare as multisets of stringified args (order-insensitive)
    msa = sorted(map(str, _args(ab)))
    msb = sorted(map(str, _args(ba)))
    assert msa == msb


# -------------------------
# Entangle (↔)
# -------------------------

def test_entangle_shape_and_args():
    a, b = "qA", "qB"
    out = entangle(a, b)
    assert _is_dict_with_op(out, "↔")
    args = _args(out)
    assert len(args) == 2
    assert args[0] == a and args[1] == b


def test_entangle_commutativity_by_multiset():
    a, b = "q1", "q2"
    ab = entangle(a, b)
    ba = entangle(b, a)
    assert _is_dict_with_op(ab, "↔")
    assert _is_dict_with_op(ba, "↔")
    msa = sorted(map(str, _args(ab)))
    msb = sorted(map(str, _args(ba)))
    assert msa == msb


# -------------------------
# Measurement (μ)
# -------------------------

def test_measure_of_superposition_collapses_to_one_branch():
    a, b = "A", "B"
    sup = superpose(a, b)
    m = measure(sup)
    assert _is_dict_with_op(m, "μ")
    collapsed = m.get("collapsed", m.get("value", None))
    assert collapsed in {a, b}


# -------------------------
# Noisy measurement (ε) - optional
# -------------------------

@pytest.mark.skipif(measurement_noisy is None, reason="measurement_noisy not implemented")
@pytest.mark.parametrize("eps", [0.0, 0.25, 1.0])
def test_measurement_noisy_bounds(eps):
    x = "stateX"
    m = measurement_noisy(x, eps)
    assert _is_dict_with_op(m, "ε")
    args = _args(m)
    assert len(args) == 2
    assert args[0] == x
    assert args[1] == eps


@pytest.mark.skipif(measurement_noisy is None, reason="measurement_noisy not implemented")
def test_measurement_noisy_returns_collapsed_or_value():
    x = "stateY"
    m = measurement_noisy(x, 0.3)
    assert _is_dict_with_op(m, "ε")
    has_any_value = ("collapsed" in m) or ("value" in m) or ("result" in m)
    assert has_any_value