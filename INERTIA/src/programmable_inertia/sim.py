from __future__ import annotations

from typing import Any, Dict, Optional
import numpy as np

from programmable_inertia.config import PIConfig


def simulate_pi(
    *,
    test_id: str,
    config: PIConfig,
    controller: Optional[Any],
    v0: float,
    v_target: float,
) -> Dict[str, Any]:
    """
    Minimal inertial plant:
        dv/dt = drive - alpha * v + noise

    Terminal velocity (noise-free): v_inf = drive / alpha
    So alpha is the "inertia/drag knob" (higher alpha => stronger resistance).
    """
    rng = np.random.default_rng(config.seed)

    v = float(v0)
    alpha = float(config.alpha0)

    v_series = np.zeros(config.steps, dtype=float)
    a_series = np.zeros(config.steps, dtype=float)
    alpha_series = np.zeros(config.steps, dtype=float)

    for t in range(config.steps):
        # optional control update
        if controller is not None:
            alpha = float(
                controller.step(alpha=alpha, v=v, v_target=v_target, t=t, rng=rng)
            )

        # plant update
        noise = float(rng.normal(0.0, config.noise_sigma)) if config.noise_sigma > 0 else 0.0
        a = float(config.drive - alpha * v + noise)
        v = float(v + config.dt * a)

        v_series[t] = v
        a_series[t] = a
        alpha_series[t] = alpha

    err_final = float(abs(v_series[-1] - v_target))

    return {
        "test_id": test_id,
        "v_target": float(v_target),
        "v_series": v_series,
        "a_series": a_series,
        "alpha_series": alpha_series,
        "v_final": float(v_series[-1]),
        "alpha_final": float(alpha_series[-1]),
        "err_final": err_final,
    }
