import pytest
import time
from backend.modules.glyphwave.entanglement.entanglement_engine import EntanglementEngine
from backend.modules.photon.memory.photon_memory_grid import PhotonMemoryGrid


@pytest.fixture
def engine():
    eng = EntanglementEngine()
    eng.pmg = PhotonMemoryGrid()
    return eng


def test_collapse_archives_into_decay_ledger(engine):
    # Setup: create a few fake waves and entangle them
    wave_a = {"id": "wave_A", "coherence": 0.98, "field_potential": 0.12}
    wave_b = {"id": "wave_B", "coherence": 0.95, "field_potential": 0.15}
    wave_c = {"id": "wave_C", "coherence": 0.90, "field_potential": 0.10}

    eid1 = engine.entangle(wave_a, wave_b)
    eid2 = engine.entangle(wave_b, wave_c)

    # Collapse all and record metrics
    metrics = engine.collapse_all()
    assert metrics["collapsed_edges"] == 2
    assert "duration_s" in metrics

    # Verify ledger archives were created
    decay_ledger = engine.pmg.get_resonance_decay_ledger()
    assert isinstance(decay_ledger, dict)
    assert eid1 in decay_ledger
    assert eid2 in decay_ledger

    # Check entry structure
    entry = decay_ledger[eid1]
    assert entry["status"] == "collapsed"
    assert "coherence_loss" in entry and "sqi_drift" in entry


def test_timestamp_progression_in_decay_records(engine):
    wave_a = {"id": "wA", "coherence": 0.9, "field_potential": 0.1}
    wave_b = {"id": "wB", "coherence": 0.88, "field_potential": 0.12}
    eid = engine.entangle(wave_a, wave_b)
    time.sleep(0.01)
    engine.collapse_all()
    ledger = engine.pmg.get_resonance_decay_ledger()
    assert ledger[eid]["timestamp"] > 0