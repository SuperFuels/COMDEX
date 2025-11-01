"""
Photon Runtime - Glyph-Math Module
──────────────────────────────────────────────
Symbolic arithmetic and encoding utilities used by PhotonLang.
Provides quantized (base-120) glyph-number system for compression
and semantic mapping of Φ, R, S, γ, ψ, κ, and other symbolic variables.
"""

# ────────────────────────────────────────────────
# Core mathematical primitives
# ────────────────────────────────────────────────
from .glyph_math_core import quantize, add, multiply, collapse, encode_time

# ────────────────────────────────────────────────
# Photon encoding and glyph translation
# ────────────────────────────────────────────────
from .encoder import photon_encode, photon_decode, encode_record

# ────────────────────────────────────────────────
# Module exports
# ────────────────────────────────────────────────
__all__ = [
    "quantize",
    "add",
    "multiply",
    "collapse",
    "encode_time",
    "photon_encode",
    "photon_decode",
    "encode_record",
]