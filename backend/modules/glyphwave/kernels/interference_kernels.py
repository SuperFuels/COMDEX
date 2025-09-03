# File: backend/modules/glyphwave/kernels/interference_kernels.py

from typing import List
import numpy as np

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.core.entangled_wave import EntangledWave
from backend.modules.symbolgraph.symbolgraph_adapter import get_bias_vector


def interfere(w1: WaveState, w2: WaveState) -> WaveState:
    """
    Interfere two WaveState objects using complex vector addition.
    Normalizes result, averages coherence, and tracks origin trace.
    """
    z1 = np.exp(1j * w1.payload["phase"]) * w1.payload["amplitude"]
    z2 = np.exp(1j * w2.payload["phase"]) * w2.payload["amplitude"]

    z_total = z1 + z2

    amplitude = np.abs(z_total)
    phase = np.angle(z_total)

    coherence = (w1.payload["coherence"] + w2.payload["coherence"]) / 2.0
    origin_trace = list(set(w1.origin_trace + w2.origin_trace))

    return WaveState(
        payload={
            "phase": phase,
            "amplitude": amplitude,
            "coherence": coherence
        },
        origin_trace=origin_trace,
        metadata={},
    )


def join_waves(waves: List[WaveState]) -> WaveState:
    """
    Join multiple waves using iterative interference logic (vector addition).
    """
    if not waves:
        raise ValueError("No waves to join.")
    result = waves[0]
    for wave in waves[1:]:
        result = interfere(result, wave)
    return result


def join_waves_batch(waves: List[WaveState]) -> WaveState:
    """
    Join multiple waves using batched complex vector addition (NumPy).
    Much faster than sequential joining for large wave lists.
    """
    if not waves:
        raise ValueError("No waves to join.")
    if len(waves) == 1:
        return waves[0]

    phases = np.array([w.payload["phase"] for w in waves])
    amplitudes = np.array([w.payload["amplitude"] for w in waves])
    z_all = np.exp(1j * phases) * amplitudes

    z_sum = np.sum(z_all, axis=0)
    amplitude = np.abs(z_sum)
    phase = np.angle(z_sum)

    coherence = np.mean([w.payload["coherence"] for w in waves])
    origin_trace = list(set(o for w in waves for o in w.origin_trace))
    timestamp = max(w.metadata.get("timestamp", 0.0) for w in waves)

    return WaveState(
        payload={
            "phase": phase,
            "amplitude": amplitude,
            "coherence": coherence
        },
        origin_trace=origin_trace,
        metadata={"timestamp": timestamp}
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
    new_phase = wave.payload["phase"] + adjusted_delta

    return WaveState(
        payload={
            "phase": new_phase,
            "amplitude": wave.payload["amplitude"],
            "coherence": wave.payload["coherence"]
        },
        origin_trace=wave.origin_trace,
        metadata=wave.metadata
    )


def boost_amplitude(wave: WaveState, factor: float) -> WaveState:
    """
    Scale the amplitude of a wave by a boost factor.
    Applies SymbolGraph bias multiplier if present.
    """
    bias = get_bias_vector(wave.origin_trace[0]) if wave.origin_trace else None
    adjusted_factor = factor * (bias.get("amplitude_boost", 1.0) if bias else 1.0)
    new_amplitude = wave.payload["amplitude"] * adjusted_factor

    return WaveState(
        payload={
            "phase": wave.payload["phase"],
            "amplitude": new_amplitude,
            "coherence": wave.payload["coherence"]
        },
        origin_trace=wave.origin_trace,
        metadata=wave.metadata
    )