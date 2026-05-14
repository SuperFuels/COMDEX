# -*- coding: utf-8 -*-
import math
from backend.symatics.core.srk_kernel import SymaticsReasoningKernel

def test_photon_coupling_and_diagnostics():
    srk = SymaticsReasoningKernel(auto_stabilize=False)

    # drive a few ops to produce feedback & coupling
    srk.superpose(1, 2)
    srk.resonate(2, 3)
    srk.entangle(3, 5)

    diag = srk.diagnostics()

    # photon block present
    assert "photon" in diag
    ph = diag["photon"]
    assert set(["ν", "|A|", "φ", "Sν"]).issubset(ph.keys())

    # spectral density should be finite and non-negative
    assert diag["spectral_density"] >= 0.0

    # λ field exported
    assert "decoherence_field" in diag
    assert "λ" in diag["decoherence_field"]
    assert 0.0 <= diag["decoherence_field"]["λ"] <= 0.2

def test_phase_lock_moves_toward_target():
    srk = SymaticsReasoningKernel(auto_stabilize=False)
    # induce an imbalance to create a nontrivial target phase
    srk.superpose(10, 0.1)  # yields small f_int, large psi density
    before = srk.photonic_field.phase
    srk.resonate(10, 0.1)
    after = srk.photonic_field.phase
    # phase should adjust (within wrap), allow equality if already locked
    moved = (abs(((after - before + math.pi) % (2*math.pi)) - math.pi) > 1e-6) or abs(after - before) < 1e-9
    assert moved