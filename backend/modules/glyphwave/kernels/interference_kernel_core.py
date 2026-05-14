# File: backend/modules/glyphwave/kernels/interference_kernel_core.py

"""
⚡ Pinned Kernel: Interference Core Logic
- Standalone performance kernel for interference computation
- Includes internal WaveState (safe copy)
- Phase 5: Used for CodexCore, GHX replay, container runtime
"""

from typing import List
import numpy as np
import time


class WaveState:
    """
    Self-contained WaveState used by pinned kernel.
    """
    def __init__(self, phase=None, amplitude=None, coherence=1.0, origin_trace=None, timestamp=None):
        self.phase = phase if phase is not None else 0.0
        self.amplitude = amplitude if amplitude is not None else 1.0
        self.coherence = coherence
        self.origin_trace = origin_trace or []
        self.timestamp = timestamp or time.time()

    def __repr__(self):
        return f"<WaveState phase={self.phase:.4f} amp={self.amplitude} coherence={self.coherence:.2f}>"


def interfere(w1: WaveState, w2: WaveState) -> WaveState:
    """
    Interfere two WaveState objects using complex vector addition.
    """
    z1 = np.exp(1j * w1.phase) * w1.amplitude
    z2 = np.exp(1j * w2.phase) * w2.amplitude
    z_total = z1 + z2

    amplitude = np.abs(z_total)
    phase = np.angle(z_total)
    coherence = (w1.coherence + w2.coherence) / 2.0
    origin_trace = list(set(w1.origin_trace + w2.origin_trace))
    timestamp = max(w1.timestamp, w2.timestamp)

    return WaveState(phase, amplitude, coherence, origin_trace, timestamp)


def join_waves(waves: List[WaveState]) -> WaveState:
    """
    Sequentially join waves via pairwise interference.
    """
    if not waves:
        raise ValueError("No waves to join.")
    result = waves[0]
    for wave in waves[1:]:
        result = interfere(result, wave)
    return result


def join_waves_batch(waves: List[WaveState]) -> WaveState:
    """
    Batched interference using fast NumPy vectorization.
    """
    if not waves:
        raise ValueError("No waves to join.")

    if len(waves) == 1:
        return waves[0]

    phases = np.array([w.phase for w in waves])
    amplitudes = np.array([w.amplitude for w in waves])
    z_all = np.exp(1j * phases) * amplitudes
    z_sum = np.sum(z_all)

    amplitude = np.abs(z_sum)
    phase = np.angle(z_sum)
    coherence = np.mean([w.coherence for w in waves])
    origin_trace = list(set(o for w in waves for o in w.origin_trace))
    timestamp = max(w.timestamp for w in waves)

    return WaveState(phase, amplitude, coherence, origin_trace, timestamp)

# -- Collapse Interface --
import logging

try:
    from backend.modules.gpu.gpu_collapse_accelerator import collapse_symbolic_wave_gpu
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

logger = logging.getLogger(__name__)


def collapse_wave_superposition(wave: WaveState, use_gpu: bool = True) -> WaveState:
    """
    Collapse symbolic wave superposition into final WaveState.
    Uses GPU acceleration if available and requested.
    """
    collapse_start = time.time()
    try:
        if use_gpu and GPU_AVAILABLE:
            collapsed = collapse_symbolic_wave_gpu(wave)
            logger.debug(f"[Collapse] GPU used for beam {getattr(wave, 'id', 'N/A')}")
        else:
            collapsed = join_waves_batch([wave])
            logger.debug(f"[Collapse] CPU fallback for beam {getattr(wave, 'id', 'N/A')}")

        collapse_time = time.time() - collapse_start
        if hasattr(collapsed, 'collapse_metadata'):
            collapsed.collapse_metadata['duration'] = collapse_time
        else:
            collapsed.collapse_metadata = {'duration': collapse_time}

        return collapsed

    except Exception as e:
        logger.error(f"[Collapse] Failed to collapse beam {getattr(wave, 'id', 'N/A')}: {e}", exc_info=True)
        # Return as-is, mark error
        wave.status = "collapse_failed"
        return wave