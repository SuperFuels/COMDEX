import asyncio
import time
import pytest

from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger
from backend.modules.photon.memory.photon_memory_grid import PhotonMemoryGrid


@pytest.mark.asyncio
async def test_resonance_link_registration_and_decay():
    """Ensure ledger registers entanglement links and applies decay over time."""
    ledger = ResonanceLedger(decay_rate=0.005)

    # Register a pair of entangled photon capsules
    result = await ledger.register_link("capsule_A", "capsule_B", phi_delta=0.1, coherence=0.98)
    assert result["status"] == "linked"
    assert ledger.get_link_state("capsule_A", "capsule_B") is not None

    # Simulate time passing for decay update
    await asyncio.sleep(0.05)
    decay_info = await ledger.decay_update()
    assert "remaining_edges" in decay_info
    assert decay_info["remaining_edges"] >= 0

    # Simulate stochastic phase drift and coherence loss
    sim_info = await ledger.simulate_decay(dt=0.2)
    assert sim_info["status"] == "simulated"

    stability = await ledger.compute_lyapunov_stability()
    assert 0.0 <= stability <= 1.0

    snapshot = await ledger.snapshot_async()
    assert "timestamp" in snapshot
    assert isinstance(snapshot, dict)


@pytest.mark.asyncio
async def test_photon_memory_grid_ledger_coupling():
    """Ensure PhotonMemoryGrid correctly synchronizes with the attached ResonanceLedger."""
    pmg = PhotonMemoryGrid()
    assert pmg._ledger is not None

    # Store two coherent states (capsules)
    capsule_a = "A1"
    capsule_b = "B1"

    state_a = {"coherence": 0.95, "phi": 0.2, "entropy": 0.01}
    state_b = {"coherence": 0.97, "phi": 0.18, "entropy": 0.02}

    await pmg.store_capsule_state(capsule_a, state_a)
    await pmg.store_capsule_state(capsule_b, state_b)

    # Link the two within PMG
    pmg.link_entanglement(capsule_a, capsule_b, phi_delta=0.02, coherence=0.96)
    links = pmg._entanglement_links
    assert f"{capsule_a}↔{capsule_b}" in links

    # Propagate resonance updates through ledger
    result = await pmg._ledger.propagate_resonance()
    assert result["status"] == "propagated"

    stability = await pmg._ledger.compute_lyapunov_stability()
    assert 0.0 <= stability <= 1.0

    # Run snapshot to ensure data integrity
    snap = await pmg._ledger.snapshot_async()
    assert isinstance(snap, dict)
    assert "timestamp" in snap