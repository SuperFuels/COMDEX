"""
Glyph-Math Core - Base-120 Quantized Symbolic Arithmetic
──────────────────────────────────────────────────────────────
Used by Photon Encoder v2 for symbolic telemetry compression.
Implements base-120 quantization and symbolic arithmetic.
"""

GLYPH_BANDS = (
    "αβγδεζηθικλμνξοπρστυφχψω"
    "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
)  # 48 primary glyphs; can be expanded to 120
BANDS = len(GLYPH_BANDS)

def quantize(value: float, bands=BANDS) -> str:
    """Quantize a float (0-1) into a symbolic glyph band."""
    if value is None:
        return "∅"
    try:
        value = max(0.0, min(1.0, float(value)))
        idx = int(value * (bands - 1))
        return GLYPH_BANDS[idx % BANDS]
    except Exception:
        return "∅"

def add(a: str, b: str) -> str:
    """⊕ - Symbolic addition (midpoint)."""
    ai, bi = GLYPH_BANDS.find(a), GLYPH_BANDS.find(b)
    if ai < 0 or bi < 0:
        return "∅"
    return GLYPH_BANDS[(ai + bi) // 2]

def multiply(a: str, b: str) -> str:
    """⟲ - Symbolic resonance (cyclic multiply)."""
    ai, bi = GLYPH_BANDS.find(a), GLYPH_BANDS.find(b)
    if ai < 0 or bi < 0:
        return "∅"
    return GLYPH_BANDS[(ai + bi) % BANDS]

def collapse(glyph: str) -> float:
    """μ - Collapse glyph back to float (0-1 range)."""
    if glyph not in GLYPH_BANDS:
        return 0.0
    return GLYPH_BANDS.index(glyph) / (BANDS - 1)

def encode_time(timestamp) -> str:
    """Convert timestamp to short symbolic form."""
    try:
        return f"τ{int(float(timestamp)) % 100000}"
    except Exception:
        return "∅"

def parse_glyph(expr):
    """
    Safe parser for symbolic glyph expressions.
    Handles malformed or single-token inputs gracefully.
    """
    try:
        parts = expr.split("=")
        if len(parts) < 2:
            # Fallback -> treat single token as neutral ψ-κ pair
            return {"ψ": 0.0, "κ": 0.0, "expr": expr}
        key, val = parts[0].strip(), float(parts[1])
        return {key: val}
    except Exception:
        return {"ψ": 0.0, "κ": 0.0, "expr": expr, "error": True}