"""
Test Suite — AION Fabric γ′-Weighted Fusion
────────────────────────────────────────────
Verifies that γ′ (feedback gain) correctly influences
the stability (σ) computation in the fusion tensor.
"""

import math
from backend.AION.fabric import aion_fabric_resonance as afr


def setup_function():
    """Reset buffer before each test."""
    afr.clear_fusion_buffer()


def test_gamma_weight_increases_stability_weighting():
    """
    When γ′ is high, deviations are penalized more strongly,
    resulting in a lower σ (stability) for the same variance.
    """
    # Baseline packets (small variation)
    packets_low_gain = [
        {"ψ": 0.8, "κ": 0.9, "T": 0.95, "Φ": 1.0, "γ′": 1.0},
        {"ψ": 0.81, "κ": 0.89, "T": 0.96, "Φ": 1.0, "γ′": 1.0},
    ]
    # Higher gain — same data, but with larger γ′
    packets_high_gain = [
        {"ψ": 0.8, "κ": 0.9, "T": 0.95, "Φ": 1.0, "γ′": 1.8},
        {"ψ": 0.81, "κ": 0.89, "T": 0.96, "Φ": 1.0, "γ′": 1.8},
    ]

    # Low gain fusion
    for p in packets_low_gain:
        afr.resonance_ingest(p)
    fused_low = afr.fuse_resonance_window()

    # Reset and run high gain fusion
    afr.clear_fusion_buffer()
    for p in packets_high_gain:
        afr.resonance_ingest(p)
    fused_high = afr.fuse_resonance_window()

    assert fused_low is not None
    assert fused_high is not None

    σ_low = fused_low["σ"]
    σ_high = fused_high["σ"]

    # Expect slightly lower σ under high γ′ (stronger variance weighting)
    assert σ_high < σ_low, f"Expected σ_high<{σ_low}, got {σ_high}"


def test_gamma_field_included_in_tensor():
    """Fusion tensor should include γ̄′ as a numeric field."""
    afr.resonance_ingest({"ψ": 1.0, "κ": 1.0, "T": 1.0, "Φ": 1.0, "γ′": 1.5})
    fused = afr.fuse_resonance_window()
    assert "γ̄′" in fused, "Fusion tensor missing γ̄′ field"
    assert math.isclose(fused["γ̄′"], 1.5, rel_tol=1e-6)


def test_gamma_default_applies_when_missing():
    """If no γ′ provided, default should be 1.0."""
    afr.resonance_ingest({"ψ": 0.9, "κ": 0.8, "T": 0.7, "Φ": 0.6})
    fused = afr.fuse_resonance_window()
    assert "γ̄′" in fused
    assert fused["γ̄′"] == 1.0