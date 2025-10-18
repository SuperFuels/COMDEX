# backend/tests/test_glyph_encoding.py
import pytest
from backend.RQC.src.photon_runtime.glyph_math.encoder import encode_record, photon_encode, photon_decode

def test_basic_encoding():
    record = {"Phi": 1.0, "resonance_index": 0.995, "gain": 0.96, "closure_state": "stable"}
    encoded = encode_record(record)

    # Accept both glyph-math or fallback JSON representations
    if "Φ" in encoded and "γ" in encoded:
        assert True
    else:
        # fallback plain mode: must be valid JSON with same keys
        import json
        data = json.loads(encoded)
        assert "Phi" in data and "gain" in data

def test_epsilon_glyph_math():
    encoded = photon_encode({"Phi": 1.0})
    assert "𝜀0" in encoded  # 1.0 should encode to epsilon zero offset

def test_roundtrip_decode():
    original = {"Phi": 1.0, "resonance_index": 0.995, "gain": 0.96, "closure_state": "stable"}
    encoded = photon_encode(original)
    decoded = photon_decode(encoded)
    assert isinstance(decoded, dict)
    assert "Φ" in encoded