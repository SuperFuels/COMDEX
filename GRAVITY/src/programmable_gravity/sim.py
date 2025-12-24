from __future__ import annotations

from typing import Any
import numpy as np

from programmable_gravity.ops import laplacian_periodic


def simulate_pg(*, test_id: str, config: Any, controller: Any, S0: np.ndarray, R_target: np.ndarray) -> dict:
    """
    Minimal deterministic simulator:
      - State: entropy-like scalar field S (NxN)
      - Curvature proxy: R = Lap(S)
      - Drift: additive Gaussian noise each step
      - Controller: optional; updates S to reduce curvature error
    Returns dict with final metrics + arrays for artifacting.
    """
    cfg = config
    rng = np.random.default_rng(int(cfg.seed))

    S = np.array(S0, dtype=float, copy=True)
    mse_series: list[float] = []

    for t in range(int(cfg.steps)):
        # drift/disturbance
        if float(cfg.drift_sigma) > 0:
            S = S + rng.normal(0.0, float(cfg.drift_sigma), size=S.shape)

        # current curvature
        R = laplacian_periodic(S)
        mse = float(np.mean((R - R_target) ** 2))
        mse_series.append(mse)

        # control
        if controller is not None:
            S = controller.step(S=S, R_target=R_target, t=t, rng=rng)

    R_final = laplacian_periodic(S)
    mse_final = float(np.mean((R_final - R_target) ** 2))

    return {
        "test_id": test_id,
        "S_final": S,
        "R_final": R_final,
        "R_target": R_target,
        "mse_series": np.asarray(mse_series, dtype=float),
        "mse_final": mse_final,
    }
