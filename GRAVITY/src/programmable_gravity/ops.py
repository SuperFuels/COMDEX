from __future__ import annotations
import numpy as np


def laplacian_periodic(x: np.ndarray) -> np.ndarray:
    """
    2D 5-point Laplacian with periodic boundary conditions.
    """
    return (
        -4.0 * x
        + np.roll(x, 1, axis=0) + np.roll(x, -1, axis=0)
        + np.roll(x, 1, axis=1) + np.roll(x, -1, axis=1)
    )


def mse(a: np.ndarray, b: np.ndarray) -> float:
    d = a - b
    return float(np.mean(d * d))


def gaussian_2d(N: int, sigma: float, amp: float = 1.0, center: tuple[int, int] | None = None) -> np.ndarray:
    """
    Deterministic centered Gaussian on an NxN grid.
    """
    if center is None:
        cx = cy = N // 2
    else:
        cx, cy = center
    xs = np.arange(N) - cx
    ys = np.arange(N) - cy
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    r2 = X * X + Y * Y
    g = np.exp(-0.5 * r2 / (sigma * sigma))
    return amp * g
