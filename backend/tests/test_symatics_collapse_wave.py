from backend.symatics.operators import OPS

def test_wave_collapse_basic():
    fn = OPS["∇"]
    out = fn({"seq": "⊕↔⟲", "coherence": 0.9, "entropy": 0.1})
    assert out["state"] == "⟲"
    assert out["pulse_ok"] is True
    assert 0.7 <= out["confidence"] <= 0.9

def test_wave_collapse_pure():
    fn = OPS["∇"]
    out = fn("⊕μ")
    assert out["state"] == "μ"

def test_wave_collapse_empty():
    fn = OPS["∇"]
    out = fn("")
    assert out["error"] == "empty"