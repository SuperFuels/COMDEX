# 📁 backend/tests/test_emit_qwave_beam.py

import asyncio
from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam
from backend.modules.glyphwave.core.wave_state import WaveState


async def run_test():
    wave = WaveState(
        wave_id="test_beam_123",
        glyph_data={"test": "data"},
        glyph_id="test_glyph",
        carrier_type="test_carrier",
        modulation_strategy="test_modulation",
        delay_ms=0,
        origin_trace=["unit_test"],
        metadata={"test_meta": True},
        prediction={"expected": "pass"},
        sqi_score=0.88,
        collapse_state="entangled",
        tick=42,
        state="active",
        container_id="test_container_001",
        source="unit_test_emit",
        target="test_target",
        timestamp=None,  # Will auto-generate
    )

    await emit_qwave_beam(
        wave=wave,
        container_id="test_container_001",
        source="unit_test_emit",
        metadata={"test_key": "✅ passed"}
    )


if __name__ == "__main__":
    asyncio.run(run_test())