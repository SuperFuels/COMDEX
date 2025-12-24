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

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, List


# ----------------------------------
# Mode flags
# ----------------------------------
LITE = os.getenv("AION_LITE") == "1"
MEANING_FILTER = os.getenv("AION_SCI_MEANING_FILTER", "0") == "1"


# Try load compressor - degrade safely if unavailable
try:
    from backend.modules.glyphos.glyph_synthesis_engine import compress_to_glyphs  # type: ignore
except Exception:
    def compress_to_glyphs(text: str) -> List[str]:
        return ["✦"]  # safe fallback glyph


# ----------------------------------
# Storage paths
# ----------------------------------
PHOTON_DIR = Path(os.getenv("AION_SCI_PHOTON_DIR", "data/photon_sci"))
PHOTON_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------
# Meaning Filter (v0.1 heuristic)
# -------------------------------
def _is_meaningful(text: str) -> bool:
    if not text or len(text) < 40:
        return False

    reasoning_markers = [
        "because", "therefore", "hence", "so that", "thus",
        "conclude", "implies", "strategy", "affects",
    ]
    tl = text.lower()
    return any(m in tl for m in reasoning_markers)


# -------------------------------
# Photon writer
# -------------------------------
def _emit_photon(event: str, text: str) -> None:
    if LITE:
        return

    if MEANING_FILTER and not _is_meaningful(text):
        return

    try:
        glyphs = compress_to_glyphs(text)
    except Exception:
        glyphs = ["✦"]

    capsule = {
        "type": "sci_photon",
        "version": "0.2",
        "event": str(event),
        "timestamp": time.time(),
        "text": text,
        "glyphs": glyphs,
        "meta": {
            "bytes": len(text),
            "preview": text[:120],
        },
    }

    # sanitize event for filenames
    safe_event = "".join(c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in str(event))[:64]
    fname = PHOTON_DIR / f"{int(time.time() * 1000)}_{safe_event}.photon"
    fname.write_text(json.dumps(capsule, ensure_ascii=False, indent=2), encoding="utf-8")


# -------------------------------
# Back-compat alias (older callers)
# -------------------------------
def _emit_photo_packet(event: str, text: str) -> None:
    _emit_photon(event, text)


# -------------------------------
# Public hook
# -------------------------------
def sci_emit(event_type: Any, data: Any) -> None:
    """
    SCI event emitter with Photon auto-archive.
    """
    try:
        text = str(data)

        # ✅ Existing behavior stays intact
        # (console / websocket / redis / telemetry etc)
        # ... your existing logger calls here ...

        # 🌌 Auto-archive SCI event as glyph capsule
        _emit_photo_packet(str(event_type), text)

    except Exception as e:
        print(f"[SCI emit] error: {e}")