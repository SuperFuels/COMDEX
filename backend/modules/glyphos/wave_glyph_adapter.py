# backend/modules/glyphos/wave_glyph_adapter.py
# 🌊 WaveGlyphAdapter
# Converts glyph execution metadata into quantum wave schemas for CodexLang -> GlyphOS coherence

import time
from typing import Dict, Any

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam


def glyph_to_wave_schema(glyph: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert glyph metadata into a wave schema structure.
    Used by GlyphExecutor and GlyphRuntime for CodexLang harmonics.
    """
    tick = context.get("tick", 0)
    container_id = context.get("container_id", "unknown")
    coord = context.get("coord", "0,0,0")

    return {
        "label": glyph,
        "phase": hash(glyph + container_id) % 360 / 360.0,
        "coherence": 0.92,
        "metadata": {
            "container_id": container_id,
            "coord": coord,
            "tick": tick,
            "origin": "wave_glyph_adapter"
        },
        "timestamp": time.time(),
    }


async def emit_wave_for_glyph(glyph: str, context: Dict[str, Any]) -> None:
    """
    Builds a WaveState from glyph data and emits a quantum wave pulse.
    """
    schema = glyph_to_wave_schema(glyph, context)
    wave = WaveState(
        wave_id=f"{glyph}_{schema['metadata']['coord']}_{schema['metadata']['tick']}",
        glow_intensity=schema["coherence"],
        pulse_frequency=schema["phase"],
        mutation_type="glyph_execution",
        mutation_cause=glyph,
        timestamp=schema["timestamp"],
    )

    try:
        await emit_qwave_beam(
            wave=wave,
            container_id=schema["metadata"]["container_id"],
            source="wave_glyph_adapter",
            metadata=schema
        )
        print(f"[🌊 WaveGlyphAdapter] Emitted wave for glyph '{glyph}' at {schema['metadata']['coord']}")
    except Exception as e:
        print(f"[⚠️] Wave emission failed for glyph '{glyph}': {e}")