# File: backend/photon_algebra/tests/test_cpu_runtime_photon.py
import pytest

from backend.codexcore_virtual.cpu_runtime import VirtualCPU
from backend.photon_algebra.core import EMPTY, TOP, BOTTOM


@pytest.fixture
def cpu_photon():
    """Create a fresh VirtualCPU in photon mode."""
    return VirtualCPU(mode="photon")


def test_simple_superpose(cpu_photon):
    instrs = [
        {"opcode": "⊕", "args": ["a", "b"]}
    ]
    out = cpu_photon.execute_instruction_list(instrs)
    # Should render as normalized ⊕
    assert out[0] in ("(a ⊕ b)", "(b ⊕ a)")


def test_absorption_rule(cpu_photon):
    # a ⊕ (a ⊗ b) → a
    instrs = [
        {"opcode": "⊕", "args": [
            "a",
            {"opcode": "⊗", "args": ["a", "b"]}
        ]}
    ]
    out = cpu_photon.execute_instruction_list(instrs)
    assert out[0] == "a"


def test_double_negation(cpu_photon):
    instrs = [
        {"opcode": "¬", "args": [
            {"opcode": "¬", "args": ["x"]}
        ]}
    ]
    out = cpu_photon.execute_instruction_list(instrs)
    assert out[0] == "x"


def test_bottom_subset_any(cpu_photon):
    # ⊥ ⊂ a → ⊤
    instrs = [
        {"opcode": "⊂", "args": [BOTTOM, "z"]}
    ]
    out = cpu_photon.execute_instruction_list(instrs)
    assert out[0] == "⊤"


def test_similarity_reflexive(cpu_photon):
    # x ≈ x → ⊤
    instrs = [
        {"opcode": "≈", "args": ["x", "x"]}
    ]
    out = cpu_photon.execute_instruction_list(instrs)
    assert out[0] == "⊤"


def test_projection_expansion(cpu_photon):
    # ★(a↔b) → (★a) ⊕ (★b)
    instrs = [
        {"opcode": "★", "args": [
            {"opcode": "↔", "args": ["m", "n"]}
        ]}
    ]
    out = cpu_photon.execute_instruction_list(instrs)
    # Either "(★m ⊕ ★n)" or normalized form
    assert "★m" in out[0] and "★n" in out[0]
    assert "⊕" in out[0]


def test_empty_identity(cpu_photon):
    instrs = [
        {"opcode": "⊕", "args": ["p", EMPTY]}
    ]
    out = cpu_photon.execute_instruction_list(instrs)
    # p ⊕ ∅ → p
    assert out[0] == "p"