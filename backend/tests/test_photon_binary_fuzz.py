# backend/tests/test_photon_binary_fuzz.py
import random
import pytest
from backend.modules.photonlang.binary_mode import to_binary, from_binary

GLYPHS = "⊕↔⟲μπ⇒∇⧖"

def random_glyph_seq(n=8):
    return "".join(random.choice(GLYPHS) for _ in range(n))

@pytest.mark.parametrize("size", [1, 2, 4, 8, 16, 32])
def test_binary_round_trip_fuzz(size):
    for _ in range(100):  # 100 fuzz rounds per size
        seq = random_glyph_seq(size)
        bits = to_binary(seq)
        assert bits, f"Binary encoder returned empty for seq {seq}"

        decoded = from_binary(bits)
        # remove unknown glyphs — this system doesn't emit any, but stay safe
        filtered = "".join(ch for ch in seq if ch in GLYPHS)

        assert decoded == filtered, f"Round-trip mismatch: {seq} -> {bits} -> {decoded}"