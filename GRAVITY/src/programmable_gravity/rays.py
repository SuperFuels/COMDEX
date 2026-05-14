from __future__ import annotations

from dataclasses import dataclass
import numpy as np


def _wrap_periodic(x: np.ndarray, N: int) -> np.ndarray:
    return np.mod(x, N)


def bilinear_sample_periodic(field: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """
    field: (N,N)
    x,y: float coords in [0,N)
    returns: sampled values (same shape as x/y)
    """
    N = field.shape[0]
    x = _wrap_periodic(x, N)
    y = _wrap_periodic(y, N)

    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    x1 = (x0 + 1) % N
    y1 = (y0 + 1) % N

    wx = x - x0
    wy = y - y0

    f00 = field[y0, x0]
    f10 = field[y0, x1]
    f01 = field[y1, x0]
    f11 = field[y1, x1]

    return (1 - wx) * (1 - wy) * f00 + wx * (1 - wy) * f10 + (1 - wx) * wy * f01 + wx * wy * f11


def grad_periodic(field: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Central-diff gradient with periodic wrap.
    Returns (d/dx, d/dy) each (N,N).
    """
    f_xp = np.roll(field, -1, axis=1)
    f_xm = np.roll(field,  1, axis=1)
    f_yp = np.roll(field, -1, axis=0)
    f_ym = np.roll(field,  1, axis=0)
    gx = 0.5 * (f_xp - f_xm)
    gy = 0.5 * (f_yp - f_ym)
    return gx, gy


@dataclass(frozen=True)
class RayResult:
    y0: np.ndarray
    y_final: np.ndarray
    deflection_mean_abs: float


def trace_rays_through_potential(
    Phi: np.ndarray,
    *,
    n_rays: int = 32,
    n_steps: int = 220,
    dt: float = 0.15,
    v0: float = 1.0,
    x_start: float = 6.0,
) -> RayResult:
    """
    Simple deterministic ray tracer:
      x,y continuous coords (periodic domain)
      v updated by a = -grad(Phi)
      integrate for n_steps

    Metric used in tests: mean absolute y deflection.
    """
    N = Phi.shape[0]
    gx, gy = grad_periodic(Phi)

    # launch rays left-ish, evenly spaced in y
    y0 = np.linspace(0.15 * N, 0.85 * N, n_rays, dtype=float)
    x = np.full_like(y0, x_start, dtype=float)
    y = y0.copy()

    vx = np.full_like(y0, v0, dtype=float)
    vy = np.zeros_like(y0, dtype=float)

    for _ in range(n_steps):
        ax = -bilinear_sample_periodic(gx, x, y)
        ay = -bilinear_sample_periodic(gy, x, y)

        vx = vx + dt * ax
        vy = vy + dt * ay

        # keep forward-ish motion stable (avoid blowups)
        speed = np.sqrt(vx * vx + vy * vy) + 1e-12
        vx = (vx / speed) * v0
        vy = (vy / speed) * v0

        x = x + dt * vx
        y = y + dt * vy

        x = _wrap_periodic(x, N)
        y = _wrap_periodic(y, N)

    # periodic y makes "deflection" ambiguous if it wraps; keep small by setup.
    y_final = y
    defl = float(np.mean(np.abs(y_final - y0)))
    return RayResult(y0=y0, y_final=y_final, deflection_mean_abs=defl)
