# File: backend/tests/test_glyph_lifecycle.py

from backend.modules.glyphwave.wave_state import WaveState
from backend.modules.glyphwave.wave_field import WaveField
import time

def test_long_lifecycle_stability():
    field = WaveField(width=32, height=32)
    glyph = WaveState.generate_sample_state(seed=777)
    field.inject_wave(glyph)

    for tick in range(10000):
        field.tick()

    assert field.get_entropy_score() < 0.95, "Entropy should remain within expected bounds"
    assert field.active_glyph_count() > 0, "At least one glyph should persist long lifecycle"