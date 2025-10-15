# backend/modules/glyphwave/kernels/superposition_kernels.py

from typing import List
import numpy as np
from backend.modules.glyphwave.core.wave_state import WaveState


def compose_superposition(waves: List[WaveState]) -> WaveState:
    """
    Compose multiple WaveStates into a single superposed wave bundle.
    Performs vector addition and tracks entanglement sources.
    """
    if not waves:
        raise ValueError("No waves provided for superposition.")

    z_total = 0j
    total_coherence = 0.0
    origin_trace = set()

    for wave in waves:
        z = np.exp(1j * wave.phase) * wave.amplitude
        z_total += z
        total_coherence += wave.coherence
        origin_trace.update(wave.origin_trace)

    amplitude = np.abs(z_total)
    phase = np.angle(z_total)
    coherence = total_coherence / len(waves)

    return WaveState(
        glyph_data={
            "phase": phase,
            "amplitude": amplitude,
            "coherence": coherence,
        },
        origin_trace=list(origin_trace),
        metadata={"superposed": True},
    )
