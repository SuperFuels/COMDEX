# backend/tests/test_photon_binary_mode.py

import pytest
from backend.modules.photonlang.binary_mode import (
    to_binary, from_binary, export_replay_frame, to_pulse_graph, GLYPH_BINARY_MAP
)

GLYPHS = "⊕↔⟲μπ->∇⧖"
BITS = [GLYPH_BINARY_MAP[g] for g in GLYPHS]

def test_round_trip_basic():
    seq = GLYPHS
    bits = to_binary(seq)
    decoded = from_binary(bits)
    assert decoded == seq

def test_export_frame_valid():
    seq = "⊕⟲μ"
    frame = export_replay_frame(seq)
    assert frame["valid"] is True
    assert frame["decode_ok"] is True
    assert frame["pulse_count"] == 3

def test_malformed_bits():
    with pytest.raises(ValueError):
        from_binary("010")  # not divisible by 4 bits

def test_unknown_symbols_ignored():
    seq = "⊕X∇Y"
    bits = to_binary(seq)
    assert bits == GLYPH_BINARY_MAP["⊕"] + GLYPH_BINARY_MAP["∇"]
    decoded = from_binary(bits)
    assert decoded == "⊕∇"

def test_sqi_lane_presence():
    graph = to_pulse_graph("⊕∇")
    assert all("sqi_lane" in p for p in graph)
    assert all(p["glyph"] in "⊕∇" for p in graph)

def test_large_stream_performance():
    seq = "⊕" * 10_000
    bits = to_binary(seq)
    assert len(bits) == 4 * 10_000
    decoded = from_binary(bits)
    assert decoded == seq