from __future__ import annotations

import numpy as np


def kgrid_1d(n: int, dx: float) -> np.ndarray:
    """Angular wavenumber grid for FFT-based spectral propagation."""
    return 2.0 * np.pi * np.fft.fftfreq(n, d=dx)


def gaussian_wavepacket(*, x: np.ndarray, x0: float, sigma: float, k0: float) -> np.ndarray:
    """Complex Gaussian wavepacket with carrier k0 (unit-normalized)."""
    x = np.asarray(x, dtype=float)
    env = np.exp(-0.5 * ((x - x0) / sigma) ** 2)
    carrier = np.exp(1j * k0 * (x - x0))
    psi = env * carrier
    # unit L2 norm
    norm = float(np.sqrt(np.sum(np.abs(psi) ** 2)))
    if norm < 1e-30:
        return psi.astype(np.complex128)
    return (psi / norm).astype(np.complex128)


def absorption_mask(*, n: int, frac: float = 0.08, strength: float = 6.0) -> np.ndarray:
    """Smooth absorber near boundaries to prevent reflections.

    Returns real mask in (0, 1]. Multiply psi by mask each step.
    """
    n_edge = max(1, int(round(frac * n)))
    idx = np.arange(n, dtype=float)

    left = np.ones(n, dtype=float)
    right = np.ones(n, dtype=float)

    # left ramp
    if n_edge > 0:
        xl = np.clip((n_edge - idx) / n_edge, 0.0, 1.0)
        left = np.exp(-strength * xl**2)

        xr = np.clip((idx - (n - 1 - n_edge)) / n_edge, 0.0, 1.0)
        right = np.exp(-strength * xr**2)

    mask = left * right
    mask = np.clip(mask, 1e-6, 1.0)
    return mask


def phase_coherence(psi: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Phase coherence score in [0, 1].

    Computes |sum(w * exp(i*angle(psi)))| / sum(w) over nonzero amplitudes.
    """
    psi = np.asarray(psi)
    amp = np.abs(psi)
    if weights is None:
        w = amp
    else:
        w = np.asarray(weights, dtype=float) * amp

    s = float(np.sum(w))
    if s < 1e-30:
        return 0.0

    ph = np.exp(1j * np.angle(psi))
    val = np.sum(w * ph)
    return float(np.abs(val) / s)
