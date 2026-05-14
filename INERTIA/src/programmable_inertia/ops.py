from __future__ import annotations
import numpy as np

def gaussian_packet_2d(N: int, sigma: float, p0: float) -> np.ndarray:
    """Complex wavepacket centered left-of-center with initial +x phase gradient."""
    x = np.arange(N)
    y = np.arange(N)
    X, Y = np.meshgrid(x, y, indexing="ij")
    x0 = N * 0.25
    y0 = N * 0.50
    amp = np.exp(-(((X - x0) ** 2 + (Y - y0) ** 2) / (2.0 * sigma**2)))
    phase = np.exp(1j * (p0 * (X - x0) / N) * 2.0 * np.pi)
    psi = amp * phase
    # normalize
    psi = psi / np.sqrt(np.sum(np.abs(psi) ** 2) + 1e-12)
    return psi.astype(np.complex128)

def centroid_x(psi: np.ndarray) -> float:
    N = psi.shape[0]
    dens = np.abs(psi) ** 2
    x = np.arange(N, dtype=float)
    cx = float(np.sum(dens.sum(axis=1) * x) / (np.sum(dens) + 1e-12))
    return cx

def l2_norm(psi: np.ndarray) -> float:
    return float(np.sqrt(np.sum(np.abs(psi) ** 2) + 1e-12))
