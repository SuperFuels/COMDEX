# File: backend/tests/test_collapse_determinism.py

import pytest
from backend.modules.glyphwave.wave_state import WaveState
from backend.modules.glyphwave.collapse_kernel import collapse_wave
import random

@pytest.mark.parametrize("seed", [42, 1337, 2025])
def test_collapse_determinism(seed):
    random.seed(seed)
    wave = WaveState.generate_sample_state(seed=seed)
    collapsed1 = collapse_wave(wave, deterministic_seed=seed)

    random.seed(seed)
    wave2 = WaveState.generate_sample_state(seed=seed)
    collapsed2 = collapse_wave(wave2, deterministic_seed=seed)

    assert collapsed1 == collapsed2, "Collapse results must match for deterministic seed"