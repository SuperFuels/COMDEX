# backend/symatics/tests/test_lambda_field.py
import numpy as np
from backend.symatics.core.lambda_field import LambdaField

def test_initialize_and_summary():
    lf = LambdaField(grid_shape=(8, 8))
    lf.initialize_law("resonance_continuity", value=1.0)
    stats = lf.summary()
    assert "resonance_continuity" in stats
    assert abs(stats["resonance_continuity"]["mean"] - 1.0) < 1e-9

def test_update_diffuses_field(monkeypatch):
    events = []
    monkeypatch.setattr("backend.symatics.core.lambda_field.record_event",
                        lambda *a, **k: events.append(k))
    lf = LambdaField(grid_shape=(4, 4), learning_rate=0.1)
    lf.initialize_law("entanglement_symmetry", 1.0)
    deviation = np.random.uniform(-0.2, 0.2, size=(4, 4))
    lf.update("entanglement_symmetry", deviation)
    stats = lf.summary()["entanglement_symmetry"]
    assert 0.8 < stats["mean"] < 1.2
    assert events and "mean_lambda" in events[0]

def test_reset_clears_field():
    lf = LambdaField()
    lf.initialize_law("collapse_energy_equivalence")
    lf.reset()
    assert lf.field == {}