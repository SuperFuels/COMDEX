from __future__ import annotations

import numpy as np

EPS = 1e-12

def l2_norm(a: np.ndarray) -> float:
    return float(np.sqrt(np.sum(np.abs(a) ** 2) + EPS))

def window(a: np.ndarray, cx: int, cy: int, r: int = 1) -> np.ndarray:
    """Periodic square window (2r+1)x(2r+1) centered at (cy,cx)."""
    h, w = a.shape
    ys = [(cy + dy) % h for dy in range(-r, r + 1)]
    xs = [(cx + dx) % w for dx in range(-r, r + 1)]
    return a[np.ix_(ys, xs)]

def corr_complex(a: np.ndarray, b: np.ndarray) -> float:
    """Normalized magnitude correlation |<a,b>| / (||a|| ||b||)."""
    na = l2_norm(a)
    nb = l2_norm(b)
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    inner = np.vdot(a, b)  # conj(a) dot b
    return float(np.abs(inner) / (na * nb + EPS))

def clip(x: float, lo: float, hi: float) -> float:
    return float(np.clip(x, lo, hi))
