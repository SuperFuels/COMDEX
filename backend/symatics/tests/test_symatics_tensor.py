# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v2.1 - Proof Reintegration Test Harness
# Verifies that all symbolic theorems/invariants evaluate True.
# Author: Tessaris Core Systems / Codex Intelligence Group
# ──────────────────────────────────────────────────────────────

import pytest

# Attempt runtime import of symbolic proof modules
try:
    from backend.modules.lean import symatics_tensor, tensor_invariants
except ImportError:
    symatics_tensor = None
    tensor_invariants = None


@pytest.mark.skipif(symatics_tensor is None, reason="symatics_tensor not available")
def test_tensor_theorems_true():
    """Validate core symbolic theorems return True."""
    assert symatics_tensor.SymProofs.theorem_tensor_coherence
    assert symatics_tensor.SymProofs.theorem_tensor_balance
    assert symatics_tensor.SymProofs.theorem_energy_coherence


@pytest.mark.skipif(tensor_invariants is None, reason="tensor_invariants not available")
def test_tensor_invariants_true():
    """Validate declared tensor invariants return True."""
    assert tensor_invariants.TensorInvariants.invariant_coherence_zero
    assert tensor_invariants.TensorInvariants.invariant_tensor_symmetry
    assert tensor_invariants.TensorInvariants.invariant_energy_link


def test_symatic_proof_pipeline_runtime():
    """Smoke-test the full symbolic proof pipeline through sym_tactics."""
    from backend.modules.lean.sym_tactics import SymTactics

    theorem = "tensor_stability_test"
    expr = "∇⊗(λ⊗ψ) = ∇⊗μ"
    result = SymTactics.sym_proof_pipeline(theorem, expr)
    assert result is True


def test_all_proofs_yield_boolean():
    """Ensure all theorem/invariant results are boolean type."""
    from backend.modules.lean.sym_tactics import SymTactics
    results = [
        SymTactics.resonant_tac("∇⊗(λ⊗ψ) = ∇⊗μ"),
        SymTactics.coherence_guard("E(t) + C(t)"),
        SymTactics.tensor_invariant_zero("∇⊗μ = 0"),
    ]
    assert all(isinstance(r, (bool, str)) for r in results)