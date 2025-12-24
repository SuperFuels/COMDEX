from __future__ import annotations
import numpy as np

def _center(N: int) -> tuple[int, int]:
    c = N // 2
    return c, c

def roi_mask_circle(N: int, radius: int) -> np.ndarray:
    cy, cx = _center(N)
    yy, xx = np.ogrid[:N, :N]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2

def roi_efficiency(intensity: np.ndarray, mask: np.ndarray) -> float:
    total = float(np.sum(intensity))
    if total <= 0:
        return 0.0
    return float(np.sum(intensity[mask]) / total)

def mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a - b) ** 2))

def _box_mean_2d(a: np.ndarray, win: int) -> np.ndarray:
    """
    Fast local box mean using an integral image, with edge padding.
    Returns same shape as a.
    """
    if win <= 1:
        return a.astype(np.float64)

    if win % 2 == 0:
        raise ValueError("win must be odd")

    N, M = a.shape
    pad = win // 2

    ap = np.pad(a.astype(np.float64), ((pad, pad), (pad, pad)), mode="edge")  # (N+2p, M+2p)
    H, W = ap.shape

    # integral image with leading zero row/col
    ii = np.zeros((H + 1, W + 1), dtype=np.float64)
    ii[1:, 1:] = np.cumsum(np.cumsum(ap, axis=0), axis=1)

    # sliding window sums for all top-left positions
    S = ii[win:, win:] - ii[:-win, win:] - ii[win:, :-win] + ii[:-win, :-win]
    # We only need the first N x M positions (corresponds to original pixels)
    return (S[:N, :M] / float(win * win))

def coherence_map(phase: np.ndarray, win: int = 7) -> np.ndarray:
    """
    Local coherence proxy:
      C(x) = | mean_{window}(exp(i*phi)) |
    Computed via box-mean on real/imag parts.
    """
    e = np.exp(1j * phase)
    mr = _box_mean_2d(e.real, win)
    mi = _box_mean_2d(e.imag, win)
    return np.sqrt(mr * mr + mi * mi)

def phase_entropy_proxy(phase: np.ndarray) -> float:
    """
    Operational entropy proxy: global phase variance.
    """
    return float(np.var(phase))

def div_info_flux(coh_map: np.ndarray, k: float = 1.0) -> np.ndarray:
    """
    J_info = -k * grad(C), so div(J_info) = -k * laplacian(C)
    """
    C = coh_map
    lap = (
        -4.0 * C
        + np.roll(C, 1, axis=0) + np.roll(C, -1, axis=0)
        + np.roll(C, 1, axis=1) + np.roll(C, -1, axis=1)
    )
    return -k * lap
