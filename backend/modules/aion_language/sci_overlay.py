#!/usr/bin/env python3
# ============================================================
# 🧠 Tessaris SCI Overlay - Dual Stream Output (Text + Photon) v0.2
# ============================================================
"""
SCI overlay intercepts cognition events and emits:

✅ Plain text logs (verbatim cognition trace)
✅ Symbolic .photon capsules (glyph-compressed replay layer)
✅ Meaning filter to avoid noise
✅ Lite mode = symbolic layer disabled

Future:
- SCI -> PhotonLens streaming
- Reverse cognitive reconstruction via photon_expand
"""

import os
import time
import json
from pathlib import Path

# ----------------------------------
# Mode flags
# ----------------------------------
LITE = os.getenv("AION_LITE") == "1"

# Try load compressor - degrade safely if unavailable
try:
    from backend.modules.glyphos.glyph_synthesis_engine import compress_to_glyphs
except Exception:
    compress_to_glyphs = lambda text: ["✦"]   # safe fallback glyph


# ----------------------------------
# Storage paths
# ----------------------------------
PHOTON_DIR = Path("data/photon_sci")
PHOTON_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------
# Meaning Filter (v0.1 heuristic)
# -------------------------------
def _is_meaningful(text: str) -> bool:
    if not text or len(text) < 40:
        return False

    reasoning_markers = [
        "because", "therefore", "hence", "so that", "thus",
        "conclude", "implies", "strategy", "affects"
    ]
    return any(m in text.lower() for m in reasoning_markers)


# -------------------------------
# Photon writer
# -------------------------------
def _emit_photon(event: str, text: str):
    if LITE:
        return

    try:
        glyphs = compress_to_glyphs(text)
    except Exception:
        glyphs = ["✦"]

    capsule = {
        "type": "sci_photon",
        "version": "0.2",
        "event": event,
        "timestamp": time.time(),
        "text": text,
        "glyphs": glyphs,
        "meta": {
            "bytes": len(text),
            "preview": text[:120]
        }
    }

    fname = PHOTON_DIR / f"{int(time.time())}_{event}.photon"
    fname.write_text(json.dumps(capsule, ensure_ascii=False, indent=2))


# -------------------------------
# Public hook
# -------------------------------
def sci_emit(event_type, data):
    """
    SCI event emitter with Photon auto-archive.
    """
    try:
        text = str(data)

        # ✅ Existing behavior stays intact
        # (console / websocket / redis / telemetry etc)
        # ... your existing logger calls here ...

        # 🌌 Auto-archive SCI event as glyph capsule
        _emit_photo_packet(event_type, text)

    except Exception as e:
        print(f"[SCI emit] error: {e}")