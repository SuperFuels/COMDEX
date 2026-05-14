# ============================================================
# Symatics v0.2 - Wave Collapse Operator (∇)
# ============================================================

from __future__ import annotations
from backend.symatics.glyphs import VALID_GLYPHS
from backend.symatics.signature import Signature

def collapse_wave(input_state: dict | str | Signature):
    """
    Wave-collapse returns stable symbolic wave truth.

    Accepts:
      * raw glyph string
      * state dict {seq, coherence, entropy}
      * Signature

    Returns canonical collapse packet:
    {
      "op": "∇",
      "state": "<glyph>",
      "freq": <symbolic frequency tag>,
      "confidence": <float>,
      "pulse_ok": bool,
    }
    """

    # ─────────────────────────────
    # Normalize input -> seq, coh, ent
    # ─────────────────────────────
    if isinstance(input_state, Signature):
        seq = input_state.meta.get("seq", "")
        coherence = input_state.meta.get("coherence", 1.0)
        entropy = input_state.meta.get("entropy", 0.0)

    elif isinstance(input_state, str):
        seq = input_state
        coherence = 1.0
        entropy = 0.0

    elif isinstance(input_state, dict):
        seq = input_state.get("seq") or input_state.get("state") or ""
        coherence = float(input_state.get("coherence", 1.0))
        entropy = float(input_state.get("entropy", 0.0))

    else:
        return {"op": "∇", "state": None, "error": "bad_state"}

    # Clean sequence: only valid glyphs
    seq = "".join(ch for ch in seq if ch in VALID_GLYPHS)

    if not seq:
        return {"op": "∇", "state": None, "error": "empty"}

    # ─────────────────────────────
    # Collapse rule
    # ─────────────────────────────
    glyph = seq[-1]
    freq = (seq.index(glyph) + 1) / max(len(seq), 1)
    confidence = max(0.0, min(1.0, coherence - entropy))

    from backend.modules.photonlang.binary_mode import to_binary
    pulse_ok = bool(to_binary(glyph))

    return {
        "op": "∇",
        "state": glyph,
        "freq": round(freq, 4),
        "confidence": round(confidence, 4),
        "pulse_ok": pulse_ok,
    }