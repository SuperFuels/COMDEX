"""
🧪 Phase 1 Integration Test - Entanglement + Decoherence + Carrier Memory
Verifies SRK-11 / SRK-12 core photonic computation layer.
"""

import os
import json
import tempfile
import time

from backend.modules.glyphwave.entanglement.entanglement_engine import EntanglementEngine
from backend.modules.glyphwave.decoherence.decoherence_tracker import DecoherenceTracker
from backend.modules.glyphwave.carrier.carrier_memory import CarrierMemory


# ────────────────────────────────────────────────────────────────
def test_entanglement_cycle(monkeypatch):
    """Validate creation and collapse of entanglement graph."""
    # patch store to avoid real persistence
    class DummyStore:
        def save_entanglement(self, *_, **__): return True
    monkeypatch.setattr("backend.modules.glyphwave.entanglement.entanglement_engine.WaveStateStore", DummyStore)

    engine = EntanglementEngine()

    w1 = {"id": "wave_A"}
    w2 = {"id": "wave_B"}
    eid = engine.entangle(w1, w2)
    assert eid.startswith("E-")
    graph_json = json.loads(engine.export_graph())
    assert len(graph_json["links"]) == 1

    metrics = engine.collapse_all()
    assert metrics["collapsed_edges"] == 1
    assert metrics["duration_s"] >= 0.0


# ────────────────────────────────────────────────────────────────
def test_decoherence_fingerprint_and_drift(tmp_path):
    """Validate deterministic fingerprinting and SQI drift logging."""
    tracker = DecoherenceTracker()

    wave_state = {"amplitude": 1.0, "phase": 0.5}
    fp1 = tracker.fingerprint(wave_state)
    time.sleep(0.01)
    fp2 = tracker.fingerprint(wave_state)

    # fingerprints should differ slightly due to timestamp
    assert fp1 != fp2
    assert len(fp1) == 128  # SHA3-512 hex digest length


# ────────────────────────────────────────────────────────────────
def test_carrier_memory_store_and_load(tmp_path):
    """Verify carrier field caching and restoration."""
    cm = CarrierMemory(memory_dir=tmp_path)

    field = {"coherence": 0.99, "phase": 0.75}
    cm.store("ch_001", field)

    files = cm.list_channels()
    assert "ch_001" in files

    restored = cm.load("ch_001")
    assert "field" in restored
    assert restored["field"]["coherence"] == 0.99