"""
Photon Runtime - Glyph Encoder
──────────────────────────────────────────────
Encodes structured telemetry dictionaries into
Photon Language glyph packets for ultra-compressed
symbolic transport between RQC -> QQC -> AION.

Usage:
    from backend.RQC.src.photon_runtime.glyph_math.encoder import photon_encode
    encoded = photon_encode(event_dict)
"""

import os
import json

# ────────────────────────────────────────────────
# 🧩 Optional Photon glyph output delegation
try:
    from backend.RQC.src.photon_runtime.glyph_math.photon_encode_v2 import photon_encode as _photon_encode_v2
except ImportError:
    _photon_encode_v2 = None

# ────────────────────────────────────────────────
# 🔹 Glyph mappings for telemetry keys
GLYPH_MAP = {
    "operator": "£",
    "timestamp": "⏱",
    "Phi": "Φ",
    "Psi": "ψ",
    "Kappa": "κ",
    "T": "Τ",
    "Phi_mean": "Φ̄",
    "Psi_mean": "ψ̄",
    "resonance_index": "∿",
    "coherence_energy": "⊕",
    "entanglement_fidelity": "↔",
    "mutual_coherence": "μ",
    "phase_correlation": "π",
    "gain": "γ",
    "closure_state": "⟲",
    "stability": "S",
    "phi_dot": "Φ̇",
}

# ────────────────────────────────────────────────
# 🔹 Numeric compression - "glyph-math"
def glyph_math(x: float) -> str:
    """
    Compress a numeric value (0-1 range) into glyph-exponent epsilon form.
    Example:
        1.0   -> ε0
        0.999 -> ε1000000
        0.95  -> ε50000000000
    """
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    if x == 1.0:
        return "ε0"
    exp = int(round(abs(x - 1.0) * 1e12))
    return f"ε{exp}"

# ────────────────────────────────────────────────
# 🔹 Main encoder
def photon_encode(data) -> str:
    """
    Encode a dictionary (or JSON string) into symbolic Photon glyph stream.

    Example output:
        "£:resonate ⏱:1760791027.87 Φ:ε0 ∿:ε3 ⊕:ε9 ↔:∅ ⟲:stable γ:ε40000000000"
    """
    if not isinstance(data, dict):
        # Try JSON decoding fallback
        try:
            data = json.loads(data)
        except Exception:
            return str(data)

    parts = []
    for k, v in data.items():
        glyph = GLYPH_MAP.get(k, k)
        if isinstance(v, float):
            v = glyph_math(v)
        elif v is None:
            v = "∅"
        elif isinstance(v, bool):
            v = "✓" if v else "✗"
        parts.append(f"{glyph}:{v}")

    return " ".join(parts)

# ────────────────────────────────────────────────
# 🔹 Environment-sensitive wrapper
def encode_record(record):
    """
    Select encoding mode:
        - Photon Glyph Mode: if PHOTON_OUTPUT=true
        - JSON (default): otherwise
    """
    if os.getenv("PHOTON_OUTPUT", "false").lower() == "true":
        # Prefer advanced Photon Encoder v2 if available
        if _photon_encode_v2:
            return _photon_encode_v2(record)
        return photon_encode(record)
    return json.dumps(record, ensure_ascii=False)

# ────────────────────────────────────────────────
# 🔹 Optional reverse decoder (future use)
def photon_decode(packet: str) -> dict:
    """
    Decode Photon glyph stream back to dictionary form.
    Example:
        "Φ:ε0 R:ε5 γ:ε2" -> {"Phi": 1.0, "R": 0.999995, "gain": 0.999998}
    """
    reverse_map = {v: k for k, v in GLYPH_MAP.items()}
    result = {}

    for token in packet.strip().split():
        if ":" not in token:
            continue
        g, v = token.split(":", 1)
        key = reverse_map.get(g, g)

        # Reverse numeric compression
        if v.startswith("ε"):
            try:
                exp = int(v[1:])
                value = 1.0 - (exp / 1e12)
                result[key] = round(value, 12)
            except Exception:
                result[key] = v
        elif v == "∅":
            result[key] = None
        elif v == "✓":
            result[key] = True
        elif v == "✗":
            result[key] = False
        else:
            result[key] = v

    return result