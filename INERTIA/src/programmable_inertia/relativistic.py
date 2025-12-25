from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import numpy as np


def _sat_factor(v: float, c_eff: float) -> float:
    """
    Saturation / cutoff proxy: dv scales down as v approaches c_eff.
    Factor = max(0, 1 - (v/c_eff)^2).
    """
    denom = max(1e-12, float(c_eff))
    x = float(v) / denom
    x = max(-0.999999, min(0.999999, x))
    return max(0.0, 1.0 - x * x)


def _controller_step(controller: Any, *, v: float, v_target: float, alpha: float, t: int, rng: np.random.Generator) -> float:
    """
    Be tolerant to controller.step signature differences.
    Preferred: step(v=..., v_target=..., alpha=..., t=..., rng=...)
    Fallbacks: step(v, v_target, alpha, t, rng) etc.
    """
    if controller is None:
        return float(alpha)

    step_fn = getattr(controller, "step", None)
    if step_fn is None:
        return float(alpha)

    # Try keyword form first (clean + stable)
    try:
        return float(step_fn(v=v, v_target=v_target, alpha=alpha, t=t, rng=rng))
    except TypeError:
        pass

    # Try fewer kwargs
    try:
        return float(step_fn(v=v, v_target=v_target, alpha=alpha, t=t))
    except TypeError:
        pass

    # Positional fallback
    try:
        return float(step_fn(v, v_target, alpha, t, rng))
    except TypeError:
        return float(step_fn(v, v_target, alpha))


def simulate_pi_relativistic(*, test_id: str, config: Mapping[str, Any], controller: Any, v_target: float) -> Dict[str, Any]:
    """
    Relativistic-ish inertia proxy:
      dv = (drive - alpha*v) * dt * (1 - (v/c_eff)^2)

    Returns JSON-serializable run dict with:
      v_final, v_target, err_final, alpha_initial, alpha_final, v_series, alpha_series
    """
    seed = int(config.get("seed", 1337))
    steps = int(config.get("steps", 420))
    dt = float(config.get("dt", 0.01))

    c_eff = float(config.get("c_eff", 0.70710678))

    alpha0 = float(config.get("alpha0", 0.55))
    alpha_min = float(config.get("alpha_min", 0.05))
    alpha_max = float(config.get("alpha_max", 0.95))

    drive0 = float(config.get("drive0", 0.0))
    drive1 = float(config.get("drive1", 1.0))

    rng = np.random.default_rng(seed)

    v = 0.0
    alpha = alpha0
    alpha_initial = alpha0

    v_series: list[float] = []
    alpha_series: list[float] = []

    for t in range(steps):
        # controller updates alpha
        alpha = _controller_step(controller, v=v, v_target=float(v_target), alpha=float(alpha), t=t, rng=rng)
        alpha = float(np.clip(alpha, alpha_min, alpha_max))

        # ramp drive to make the wall show up
        frac = t / max(1, steps - 1)
        drive = drive0 + (drive1 - drive0) * frac

        dv = (drive - alpha * v) * dt
        dv *= _sat_factor(v, c_eff)

        v = v + dv

        v_series.append(float(v))
        alpha_series.append(float(alpha))

    v_final = float(v_series[-1]) if v_series else float(v)
    alpha_final = float(alpha_series[-1]) if alpha_series else float(alpha)

    run: Dict[str, Any] = dict(
        test_id=str(test_id),
        v_target=float(v_target),
        v_final=v_final,
        err_final=float(abs(v_final - float(v_target))),
        alpha_initial=float(alpha_initial),
        alpha_final=float(alpha_final),
        v_series=v_series,
        alpha_series=alpha_series,
    )
    return run
