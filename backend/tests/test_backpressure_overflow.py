# File: backend/tests/test_backpressure_overflow.py

from backend.modules.glyphwave.wave_field import WaveField
from backend.modules.glyphwave.wave_state import WaveState

def test_backpressure_decay_behavior():
    field = WaveField(width=16, height=16)

    # Inject glyphs rapidly to simulate overload
    for i in range(1000):
        wave = WaveState.generate_sample_state(seed=i)
        field.inject_wave(wave)

    field.tick(batch_size=500)  # Force simulated backpressure

    assert field.get_backpressure() < 1.0, "Backpressure should stabilize below 1.0"
    assert field.evicted_glyphs_count() > 0, "Some glyphs should be decayed or evicted"