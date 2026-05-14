from __future__ import annotations

import numpy as np


def laplacian_1d(u: np.ndarray) -> np.ndarray:
    """Periodic 1D Laplacian."""
    return np.roll(u, -1) - 2.0 * u + np.roll(u, 1)


def prob_density(u: np.ndarray) -> np.ndarray:
    """Non-negative density proxy."""
    return np.square(u.astype(float))


def peak(p: np.ndarray) -> float:
    return float(np.max(p))


def centroid(p: np.ndarray) -> float:
    w = float(np.sum(p))
    if w <= 0.0:
        return float(len(p) // 2)
    i = np.arange(len(p), dtype=float)
    return float(np.sum(i * p) / w)


def sigma_width(p: np.ndarray) -> float:
    """Std-dev width around centroid (robust)."""
    w = float(np.sum(p))
    if w <= 0.0:
        return 0.0
    c = centroid(p)
    i = np.arange(len(p), dtype=float)
    var = float(np.sum(((i - c) ** 2) * p) / w)
    return float(np.sqrt(max(var, 0.0)))


def fwhm_width_from_sigma(sig: float) -> float:
    """Gaussian approx: FWHM ~= 2.355*sigma."""
    return float(2.35482004503 * sig)


def l2_norm(u: np.ndarray) -> float:
    return float(np.sqrt(np.sum(np.square(u.astype(float)))))


def summarize_series(peaks: list[float], widths: list[float], norms: list[float]) -> dict:
    p0 = float(peaks[0])
    pT = float(peaks[-1])
    w0 = float(widths[0])
    wT = float(widths[-1])

    # Correct (non-inverted) retention
    peak_retention = pT / (p0 + 1e-12)

    # Width drift % (robust vs w0 ~ 0)
    denom = max(w0, 1e-9)
    width_drift_pct = abs(wT - w0) / denom * 100.0

    return {
        "peak0": p0,
        "peakT": pT,
        "width0": w0,
        "widthT": wT,
        "peak_retention": float(peak_retention),
        "width_drift_pct": float(width_drift_pct),
        "max_norm": float(np.max(norms)),
    }
