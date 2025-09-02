# File: backend/modules/glyphwave/kernels/interference_kernels.py
from typing import List
import numpy as np

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.core.entangled_wave import EntangledWave

# ✅ SymbolGraph bias adapter
from backend.modules.symbolic.adapters.symbolgraph_adapter import get_bias_vector


def interfere(w1: WaveState, w2: WaveState) -> WaveState:
    """
    Interfere two WaveState objects using complex vector addition.
    Normalizes result, averages coherence, and tracks origin trace.
    """
    z1 = np.exp(1j * w1.phase) * w1.amplitude
    z2 = np.exp(1j * w2.phase) * w2.amplitude

    z_total = z1 + z2

    amplitude = np.abs(z_total)
    phase = np.angle(z_total)

    coherence = (w1.coherence + w2.coherence) / 2.0
    origin_trace = list(set(w1.origin_trace + w2.origin_trace))

    return WaveState(
        phase=phase,
        amplitude=amplitude,
        coherence=coherence,
        origin_trace=origin_trace,
        timestamp=max(w1.timestamp, w2.timestamp)
    )


def entangle(waves: List[WaveState], mode: str = "bidirectional") -> EntangledWave:
    """
    Wrap a list of WaveState objects into an entangled structure.
    Supports 'bidirectional' or 'fused' entanglement strategies.
    """
    if not waves:
        raise ValueError("Cannot entangle an empty list of waves.")

    entangled = EntangledWave(mode=mode)

    for i, wave in enumerate(waves):
        entangled.add_wave(wave, index=i)

    entangled.generate_links()

    return entangled


def phase_shift(wave: WaveState, delta_phase: float) -> WaveState:
    """
    Shift the phase of a wave by delta_phase (radians).
    Also applies SymbolGraph bias if available.
    """
    bias = get_bias_vector(wave.origin_trace[0]) if wave.origin_trace else None
    adjusted_delta = delta_phase + (bias.get("phase_shift", 0.0) if bias else 0.0)

    return WaveState(
        phase=wave.phase + adjusted_delta,
        amplitude=wave.amplitude,
        coherence=wave.coherence,
        origin_trace=wave.origin_trace,
        timestamp=wave.timestamp
    )


def boost_amplitude(wave: WaveState, factor: float) -> WaveState:
    """
    Scale the amplitude of a wave by a boost factor.
    Applies SymbolGraph bias multiplier if present.
    """
    bias = get_bias_vector(wave.origin_trace[0]) if wave.origin_trace else None
    adjusted_factor = factor * (bias.get("amplitude_boost", 1.0) if bias else 1.0)

    return WaveState(
        phase=wave.phase,
        amplitude=wave.amplitude * adjusted_factor,
        coherence=wave.coherence,
        origin_trace=wave.origin_trace,
        timestamp=wave.timestamp
    )


def join_waves(waves: List[WaveState]) -> WaveState:
    """
    Join multiple waves using interference logic (vector addition).
    """
    if not waves:
        raise ValueError("No waves to join.")

    result = waves[0]
    for wave in waves[1:]:
        result = interfere(result, wave)
    return result