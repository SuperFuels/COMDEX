from __future__ import annotations

from dataclasses import dataclass
import numpy as np


def _poisson_solve_from_laplacian_periodic(R: np.ndarray) -> np.ndarray:
    """
    Solve Lap(S) = R on a 2D periodic grid using FFT.
    Assumes Lap is the standard 5-point periodic Laplacian:
        Lap(S) = roll_x+ + roll_x- + roll_y+ + roll_y- - 4*S
    The DC mode is set to 0 (solution defined up to constant).
    """
    if R.ndim != 2 or R.shape[0] != R.shape[1]:
        raise ValueError("R must be square 2D array")

    N = R.shape[0]
    R_hat = np.fft.fftn(R)

    # Discrete Laplacian eigenvalues for periodic 2D grid
    # lambda(kx,ky) = 2cos(2pi kx/N) + 2cos(2pi ky/N) - 4
    k = np.fft.fftfreq(N)  # cycles per sample
    theta = 2.0 * np.pi * k
    cx = np.cos(theta)[:, None]
    cy = np.cos(theta)[None, :]
    lam = (2.0 * cx + 2.0 * cy - 4.0)

    S_hat = np.zeros_like(R_hat, dtype=np.complex128)
    mask = lam != 0.0
    S_hat[mask] = R_hat[mask] / lam[mask]
    S_hat[0, 0] = 0.0  # fix gauge (mean = 0)

    S = np.fft.ifftn(S_hat).real
    return S


@dataclass
class CurvatureHoldController:
    lr: float = 0.25
    max_step: float = 0.25

    @property
    def name(self) -> str:
        return "tessaris_curvature_hold"

    def __post_init__(self) -> None:
        self._S_star: np.ndarray | None = None

    def step(self, *, S: np.ndarray, R_target: np.ndarray, t: int, rng: np.random.Generator) -> np.ndarray:
        # Build cached S_star such that Lap(S_star) == R_target
        if self._S_star is None:
            self._S_star = _poisson_solve_from_laplacian_periodic(R_target).astype(float)

        dS = self.lr * (self._S_star - S)
        dS = np.clip(dS, -self.max_step, self.max_step)
        return (S + dS).astype(float)


@dataclass
class RandomJitterController:
    sigma: float = 0.02

    @property
    def name(self) -> str:
        return "random_jitter"

    def step(self, *, S: np.ndarray, R_target: np.ndarray, t: int, rng: np.random.Generator) -> np.ndarray:
        return (S + rng.normal(0.0, self.sigma, size=S.shape)).astype(float)
