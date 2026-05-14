# File: backend/tests/test_entanglement_integrity.py

from backend.modules.glyphwave.wave_state import WaveState
from backend.modules.glyphwave.entanglement import entangle_waves, resolve_entanglement

def test_entangle_to_collapse_integrity():
    wave_a = WaveState.generate_sample_state(seed=101)
    wave_b = WaveState.generate_sample_state(seed=202)

    entangled = entangle_waves(wave_a, wave_b)
    collapsed = resolve_entanglement(entangled)

    assert collapsed is not None, "Collapsed wave should not be None"
    assert collapsed.metadata.get("entangled_from") == (wave_a.id, wave_b.id)