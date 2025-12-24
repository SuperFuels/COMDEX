from __future__ import annotations
import numpy as np

def make_input_field(N: int, seed: int) -> np.ndarray:
    """
    Benchmark input: plane wave (unit amplitude, zero phase).
    The controller owns the phase mask; drift is applied separately.
    """
    return np.ones((N, N), dtype=np.complex128)

def fft_propagate(U: np.ndarray) -> np.ndarray:
    """
    Toy propagation: focal plane is FFT of aperture field.
    """
    return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(U)))

def intensity_from_field(U: np.ndarray) -> np.ndarray:
    I = np.abs(U) ** 2
    s = np.sum(I)
    if s > 0:
        I = I / s
    return I

def random_walk_phase(N: int, rng: np.random.Generator, sigma: float) -> np.ndarray:
    """
    Phase drift: random-walk *tilt increment* (global linear ramp increment).
    Returned array is an increment; caller accumulates it (env_phase += inc).
    sigma is std-dev of per-step tilt increment (radians per pixel).
    """
    dkx = float(rng.normal(0.0, sigma))
    dky = float(rng.normal(0.0, sigma))

    yy, xx = np.mgrid[:N, :N]
    cy = (N - 1) / 2.0
    cx = (N - 1) / 2.0
    return dkx * (xx - cx) + dky * (yy - cy)

