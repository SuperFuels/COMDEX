from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np

from .ops import b_eff_from_j, ddx, ddy, laplacian, angle_between, vec_norm2


def simulate_pm(
    *,
    test_id: str,
    config: Mapping[str, Any],
    controller,
    b_target: np.ndarray,
) -> Dict[str, Any]:
    """Minimal 2D lattice vector-field sim (audit-safe proxy)."""

    seed = int(config.get("seed", 1337))
    rng = np.random.default_rng(seed)

    n = int(config.get("n", 32))
    steps = int(config.get("steps", 900))
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

    vx = rng.normal(0.0, 1e-3, size=(n, n))
    vy = rng.normal(0.0, 1e-3, size=(n, n))

    kappa = float(kappa0)
    kappa_initial = float(kappa0)

    t_series: list[float] = []
    k_series: list[float] = []
    b0_series: list[float] = []
    b1_series: list[float] = []
    bmag_series: list[float] = []
    ang_series: list[float] = []

    b_target = np.asarray(b_target, dtype=float)

    for t in range(steps):
        drive = drive0 + (drive1 - drive0) * (t / max(1, steps - 1))

        b_eff = b_eff_from_j(vx, vy, dx, dy)
        bmag = vec_norm2(b_eff)
        ang = angle_between(b_eff, b_target)

        if controller is not None:
            kappa = float(controller.step(kappa=kappa, angle_err=ang, t=t, rng=rng))
        kappa = float(np.clip(kappa, kappa_min, kappa_max))

        lvx = laplacian(vx, dx, dy)
        lvy = laplacian(vy, dx, dy)

        vx = vx + dt * (drive - alpha * vx + nu * lvx - kappa * ddy(vx, dy))
        vy = vy + dt * (0.0  - alpha * vy + nu * lvy + kappa * ddx(vy, dx))

        t_series.append(float(t * dt))
        k_series.append(float(kappa))
        b0_series.append(float(b_eff[0]))
        b1_series.append(float(b_eff[1]))
        bmag_series.append(float(bmag))
        ang_series.append(float(ang))

    return dict(
        test_id=test_id,
        config=dict(config),
        b_target=[float(b_target[0]), float(b_target[1])],
        b_final=[float(b0_series[-1]), float(b1_series[-1])],
        bmag_final=float(bmag_series[-1]),
        ang_err_final=float(ang_series[-1]),
        kappa_initial=float(kappa_initial),
        kappa_final=float(k_series[-1]),
        t_series=t_series,
        kappa_series=k_series,
        b0_series=b0_series,
        b1_series=b1_series,
        bmag_series=bmag_series,
        ang_err_series=ang_series,
    )