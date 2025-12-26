from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np

from .ops import laplacian


def simulate_containment(
    *,
    test_id: str,
    config: Mapping[str, Any],
    controller,
) -> Dict[str, Any]:
    """
    MG02 containment plant (audit-safe):

    Scalar packet rho on a periodic lattice.
    - Diffuses (D * Laplacian)
    - Global damping (alpha)
    - Outward drift ("pressure") pushes mass away from center (beta term)
    - Containment damping outside a radius: -gamma * mask_outside * rho

    Leak metric:
      leak := sum(|rho| outside) / sum(|rho| total)

    Controller adjusts gamma to minimize leak (model-only).
    """
    seed = int(config.get("seed", 2026))
    rng = np.random.default_rng(seed)

    n = int(config.get("n", 64))
    steps = int(config.get("steps", 1400))
    dt = float(config.get("dt", 0.01))
    dx = float(config.get("dx", 1.0))
    dy = float(config.get("dy", 1.0))

    D = float(config.get("D", 0.18))          # diffusion strength
    alpha = float(config.get("alpha", 0.01))  # global damping

    beta = float(config.get("beta", 0.06))    # outward drift strength

    gamma0 = float(config.get("gamma0", 0.0))
    gamma_min = float(config.get("gamma_min", 0.0))
    gamma_max = float(config.get("gamma_max", 6.0))

    r_frac = float(config.get("r_frac", 0.35))

    cx = (n - 1) / 2.0
    cy = (n - 1) / 2.0

    yy, xx = np.mgrid[0:n, 0:n]
    x = (xx - cx)
    y = (yy - cy)
    rr = np.sqrt(x * x + y * y) + 1e-12
    ux = x / rr
    uy = y / rr

    r0 = r_frac * (n / 2.0)
    mask_outside = (rr > r0).astype(float)

    sigma = float(config.get("sigma", 2.5))
    rho = np.exp(-(rr**2) / (2.0 * sigma**2)).astype(float)
    rho += rng.normal(0.0, 1e-6, size=(n, n))

    gamma = float(gamma0)
    gamma_initial = float(gamma0)

    t_series: list[float] = []
    gamma_series: list[float] = []
    leak_series: list[float] = []
    mass_total_series: list[float] = []
    mass_out_series: list[float] = []

    eps = 1e-12

    for t in range(steps):
        abs_rho = np.abs(rho)
        mass_total = float(np.sum(abs_rho))
        mass_out = float(np.sum(abs_rho * mask_outside))
        leak = float(mass_out / (mass_total + eps))

        if controller is not None:
            gamma = float(controller.step(gamma=gamma, leak=leak, t=t, rng=rng))
        gamma = float(np.clip(gamma, gamma_min, gamma_max))

        # outward drift (advection): -beta * div(rho * u_hat)
        jx = rho * ux
        jy = rho * uy
        div_j = (np.roll(jx, -1, axis=1) - np.roll(jx, 1, axis=1)) / (2.0 * dx) + (
            np.roll(jy, -1, axis=0) - np.roll(jy, 1, axis=0)
        ) / (2.0 * dy)

        lrho = laplacian(rho, dx, dy)
        rho = rho + dt * (D * lrho - alpha * rho - beta * div_j - gamma * mask_outside * rho)

        t_series.append(float(t * dt))
        gamma_series.append(float(gamma))
        leak_series.append(float(leak))
        mass_total_series.append(float(mass_total))
        mass_out_series.append(float(mass_out))

    run = dict(
        test_id=test_id,
        config=dict(config),
        leak_final=float(leak_series[-1]),
        leak_series=leak_series,
        gamma_initial=float(gamma_initial),
        gamma_final=float(gamma_series[-1]),
        t_series=t_series,
        gamma_series=gamma_series,
        mass_total_series=mass_total_series,
        mass_out_series=mass_out_series,
    )
    return run
