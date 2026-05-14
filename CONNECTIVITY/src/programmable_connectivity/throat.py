from __future__ import annotations

import numpy as np

from .ops import clip

def apply_throat_coupling(
    psi: np.ndarray,
    *,
    a: tuple[int, int],
    b: tuple[int, int],
    eta: float,
    sigma: float,
    dt: float,
) -> None:
    """
    ER=EPR-inspired throat coupling between two lattice coordinates.
    a,b are (x,y) tuples. We mix complex amplitudes at those sites.

    eta   : throat conductance (canon pin: ~0.9974)
    sigma : cross-domain coupling gate (0..1), "Sigma-control"
    """
    eta = clip(eta, 0.0, 1.0)
    sigma = clip(sigma, 0.0, 1.0)
    x1, y1 = a
    x2, y2 = b

    p1 = psi[y1, x1]
    p2 = psi[y2, x2]

    k = sigma * eta
    d12 = (p2 - p1)
    psi[y1, x1] = p1 + dt * k * d12
    psi[y2, x2] = p2 - dt * k * d12
