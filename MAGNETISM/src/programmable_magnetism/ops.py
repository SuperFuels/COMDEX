from __future__ import annotations

import numpy as np


def ddx(a: np.ndarray, dx: float) -> np.ndarray:
    return (np.roll(a, -1, axis=1) - np.roll(a, 1, axis=1)) / (2.0 * dx)


def ddy(a: np.ndarray, dy: float) -> np.ndarray:
    return (np.roll(a, -1, axis=0) - np.roll(a, 1, axis=0)) / (2.0 * dy)


def laplacian(a: np.ndarray, dx: float, dy: float) -> np.ndarray:
    return (
        (np.roll(a, -1, axis=0) - 2.0 * a + np.roll(a, 1, axis=0)) / (dy * dy)
        + (np.roll(a, -1, axis=1) - 2.0 * a + np.roll(a, 1, axis=1)) / (dx * dx)
    )


def rms(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(x * x)))


def vec_norm2(v: np.ndarray) -> float:
    v = np.asarray(v, dtype=float)
    return float(np.sqrt(np.sum(v * v)))


def wrap_pi(a: float) -> float:
    return float((a + np.pi) % (2.0 * np.pi) - np.pi)


def angle_between(u: np.ndarray, v: np.ndarray) -> float:
    """Absolute angle between 2D vectors (radians). If either is near-zero, returns pi."""
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    nu = vec_norm2(u)
    nv = vec_norm2(v)
    if nu < 1e-12 or nv < 1e-12:
        return float(np.pi)

    dot = float(u[0] * v[0] + u[1] * v[1])
    det = float(u[0] * v[1] - u[1] * v[0])
    ang = float(np.arctan2(det, dot))
    return abs(wrap_pi(ang))


def b_eff_from_j(vx: np.ndarray, vy: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Audit-safe 2D 'magnetic proxy' vector from J_info ~ (vx, vy).

    With periodic boundaries, mean derivatives are ~0, so we use RMS:
      Bx := RMS( ∂vy/∂x )
      By := RMS( -∂vx/∂y )
    """
    bx = rms(ddx(vy, dx))
    by = rms(-ddy(vx, dy))
    return np.array([bx, by], dtype=float)