"""
Photon Encoder v2 — Symbolic Telemetry Compression
──────────────────────────────────────────────────────────────
Encodes Φ, R, S, γ as glyph-math numbers for Photon output mode.
"""

import json
from .glyph_math_core import quantize, encode_time

def photon_encode(record: dict) -> str:
    """Convert a telemetry record into a compact Photon glyph line."""
    Φ = quantize(record.get("Φ_mean") or record.get("Phi"))
    R = quantize(record.get("resonance_index"))
    S = record.get("closure_state", "∅")
    γ = quantize(record.get("gain"))
    t = encode_time(record.get("timestamp"))

    # Photon packet — symbolic capsule, not JSON
    return f"data: ⏱:{t} Φ:{Φ} R:{R} S:{S} γ:{γ}\n\n"