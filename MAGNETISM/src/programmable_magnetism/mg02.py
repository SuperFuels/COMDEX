from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np

from .ops import b_eff_from_j, ddx, ddy, laplacian, angle_between, vec_norm2, rms


def _periodic_r2(n: int) -> np.ndarray:
    """
    Squared distance to center under periodic wrap.
    """
    cx = n // 2
    cy = n // 2
    ys = np.arange(n)
    xs = np.arange(n)
    yy, xx = np.meshgrid(ys, xs, indexing="ij")

    dx = np.minimum(np.abs(xx - cx), n - np.abs(xx - cx))
    dy = np.minimum(np.abs(yy - cy), n - np.abs(yy - cy))
    return (dx * dx + dy * dy).astype(float)


def _gaussian_packet(n: int, sigma: float = 2.0) -> np.ndarray:
    r2 = _periodic_r2(n)
    g = np.exp(-0.5 * r2 / (sigma * sigma))
    g = g / float(np.sum(g) + 1e-12)
    return g.astype(float)


def simulate_mg02_containment(
    *,
    test_id: str,
    config: Mapping[str, Any],
    controller,
    b_target: np.ndarray,
) -> Dict[str, Any]:
    """
    MG02: Causal Containment ("Magnetic Bottle") — audit-safe proxy.

    We evolve:
      - (vx, vy) as MG01 plant
      - a scalar packet rho that tends to diffuse/advect outward
        but is "contained" by higher kappa.

    Key idea:
      kappa acts like a containment strength:
        - higher kappa reduces effective diffusion / outward drift of rho
      controller adjusts kappa using angle_err feedback (MG01 logic)

    Metric:
      leakage(t) = mass outside radius R
      spread(t)  = sqrt( mean(r^2) ) under periodic center
    """
    seed = int(config.get("seed", 1337))
    rng = np.random.default_rng(seed)

    n = int(config.get("n", 48))
    steps = int(config.get("steps", 1500))
    dt = float(config.get("dt", 0.01))
    dx = float(config.get("dx", 1.0))
    dy = float(config.get("dy", 1.0))

    alpha = float(config.get("alpha", 0.10))
    nu = float(config.get("nu", 0.08))

    drive0 = float(config.get("drive0", 0.0))
    drive1 = float(config.get("drive1", 1.0))

    kappa0 = float(config.get("kappa0", 0.60))
    kappa_min = float(config.get("kappa_min", 0.0))
    kappa_max = float(config.get("kappa_max", 3.0))

    # rho dynamics knobs
    D0 = float(config.get("rho_D0", 0.35))         # base diffusion
    drift0 = float(config.get("rho_drift0", 0.35)) # base outward drift
    R = float(config.get("rho_R", max(4.0, n / 6.0)))

    vx = rng.normal(0.0, 1e-3, size=(n, n))
    vy = rng.normal(0.0, 1e-3, size=(n, n))
    rho = _gaussian_packet(n, sigma=float(config.get("rho_sigma", 2.0)))

    kappa = float(kappa0)
    kappa_initial = float(kappa0)

    r2 = _periodic_r2(n)
    r = np.sqrt(r2)
    outside = (r >= R).astype(float)

    b_target = np.asarray(b_target, dtype=float)

    t_series: list[float] = []
    k_series: list[float] = []
    ang_series: list[float] = []
    bmag_series: list[float] = []
    leakage_series: list[float] = []
    spread_series: list[float] = []

    for t in range(steps):
        drive = drive0 + (drive1 - drive0) * (t / max(1, steps - 1))

        b_eff = b_eff_from_j(vx, vy, dx, dy)
        bmag = vec_norm2(b_eff)
        ang = angle_between(b_eff, b_target)

        if controller is not None:
            kappa = float(controller.step(kappa=kappa, angle_err=ang, t=t, rng=rng))
        kappa = float(np.clip(kappa, kappa_min, kappa_max))

        # plant update (same structural form as MG01)
        lvx = laplacian(vx, dx, dy)
        lvy = laplacian(vy, dx, dy)
        vx = vx + dt * (drive - alpha * vx + nu * lvx - kappa * ddy(vx, dy))
        vy = vy + dt * (0.0  - alpha * vy + nu * lvy + kappa * ddx(vy, dx))

        # containment proxy:
        # higher kappa => stronger "bottle" => lower diffusion and lower outward drift
        bottle = 1.0 + float(kappa)
        D = D0 / bottle
        drift = drift0 / bottle

        # outward advection term: -drift * (r_hat · grad rho)
        # approximate r_hat dot grad via normalized (x,y) * (ddx, ddy)
        # Using periodic center, build r_hat fields once.
        # We avoid dividing by 0 at center with eps.
        eps = 1e-9
        # derive r_hat components from periodic shortest dx,dy
        # recompute cheaply using rolls: approximate radial direction by gradients of r
        # (good enough for audit-safe proxy)
        drdx = ddx(r, dx)
        drdy = ddy(r, dy)
        norm = np.sqrt(drdx * drdx + drdy * drdy) + eps
        rhx = drdx / norm
        rhy = drdy / norm

        adv = rhx * ddx(rho, dx) + rhy * ddy(rho, dy)
        rho = rho + dt * (-drift * adv + D * laplacian(rho, dx, dy))

        # keep rho as a probability-like mass
        rho = np.clip(rho, 0.0, None)
        s = float(np.sum(rho) + 1e-12)
        rho = rho / s

        leakage = float(np.sum(rho * outside))
        spread = float(np.sqrt(np.sum(rho * r2)))

        t_series.append(float(t * dt))
        k_series.append(float(kappa))
        ang_series.append(float(ang))
        bmag_series.append(float(bmag))
        leakage_series.append(leakage)
        spread_series.append(spread)

    run = dict(
        test_id=test_id,
        config=dict(config),
        b_target=[float(b_target[0]), float(b_target[1])],
        kappa_initial=kappa_initial,
        kappa_final=float(k_series[-1]),
        bmag_final=float(bmag_series[-1]),
        ang_err_final=float(ang_series[-1]),
        leakage_final=float(leakage_series[-1]),
        spread_final=float(spread_series[-1]),
        t_series=t_series,
        kappa_series=k_series,
        ang_err_series=ang_series,
        bmag_series=bmag_series,
        leakage_series=leakage_series,
        spread_series=spread_series,
    )
    return run
