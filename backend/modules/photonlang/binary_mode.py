"""
PhotonLang Binary Mode — v0.2
Symbolic → reversible binary tape for photon microcode lanes.
Ensures deterministic round-trip & SQI-pulse propagation.
"""

from __future__ import annotations

# ------------------------------------------------------------
# Symbol → Bit mapping (4-bit lane, v0.2)
# ------------------------------------------------------------
GLYPH_BINARY_MAP = {
    "⊕": "0001",  # superpose
    "↔": "0010",  # entangle
    "⟲": "0011",  # resonate
    "μ": "0100",  # measure
    "π": "0101",  # project
    "⇒": "0110",  # trigger
    "∇": "0111",  # collapse
    "⧖": "1000",  # modulate
}

REVERSE_MAP = {v: k for k, v in GLYPH_BINARY_MAP.items()}

# reserved lanes for SQI pulses & internal tape control
LANE_SQI = "1110"
LANE_PAD = "0000"  # zero-width pad for wave lane sync


# ------------------------------------------------------------
# Encode / Decode
# ------------------------------------------------------------
def to_binary(seq: str) -> str:
    bits = []
    for ch in seq:
        lane = GLYPH_BINARY_MAP.get(ch)
        if lane:
            bits.append(lane)
    return "".join(bits) if bits else ""


def from_binary(bits: str) -> str:
    if not bits:
        return ""

    if len(bits) % 4 != 0:
        raise ValueError("Binary length must be multiple of 4 bits")

    out = []
    for i in range(0, len(bits), 4):
        chunk = bits[i:i+4]
        out.append(REVERSE_MAP.get(chunk, "?"))
    return "".join(out)


# ------------------------------------------------------------
# Export & Pulse Integrity Check
# ------------------------------------------------------------
def export_replay_frame(seq: str) -> dict:
    bits = to_binary(seq)
    decoded = from_binary(bits)

    # remove ignored / unknown glyphs during round-trip compare
    filtered = "".join(ch for ch in seq if ch in GLYPH_BINARY_MAP)
    decode_ok = decoded == filtered

    return {
        "glyphs": seq,
        "binary": bits,
        "decode_ok": decode_ok,
        "valid": bool(bits),
        "pulse_count": len(bits) // 4,
    }


# ------------------------------------------------------------
# Microcode lane binding (v0.2)
# For future hardware / QQC cross-bridge
# ------------------------------------------------------------
def to_pulse_graph(seq: str) -> list[dict]:
    """Emit structured microcode pulses for internal execution lanes."""
    pulses = []
    for ch in seq:
        lane = GLYPH_BINARY_MAP.get(ch)
        if not lane:
            continue
        pulses.append({
            "glyph": ch,
            "bits": lane,
            "sqi_lane": LANE_SQI,
            "time": None,      # waveform clock set at runtime
            "coherence": None, # SQI hook
        })
    return pulses