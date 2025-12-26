from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TransmissionLockController:
    """Closed-loop controller for barrier height V0.

    Goal: drive final transmission T toward T_target.

    Convention:
      - If transmission is too high, increase V0 (make barrier stronger).
      - If transmission is too low, decrease V0.

    Audit-safe: model-only feedback.
    """

    lr: float = 12.0
    v0_min: float = 0.0
    v0_max: float = 8.0
    smooth: float = 0.05
    name: str = "tessaris_transmission_lock"

    def step(
        self,
        *,
        v0: float,
        t: int,
        t_steps: int,
        T: float,
        T_target: float,
        rng: np.random.Generator,
    ) -> float:
        # Prefer late-stage correction (when packet reaches barrier/right side)
        frac = t / max(1, t_steps - 1)
        gain = self.lr * (0.2 + 0.8 * frac)

        err = float(T - T_target)  # + => too much transmission
        v_new = float(v0 + gain * err)
        v_new = (1.0 - self.smooth) * v_new + self.smooth * float(v0)
        return float(np.clip(v_new, self.v0_min, self.v0_max))


@dataclass
class RandomJitterBarrierController:
    """Baseline: random jitter on barrier height V0 (no feedback)."""

    sigma: float = 1.0
    v0_min: float = 0.0
    v0_max: float = 8.0
    name: str = "random_jitter_barrier"

    def step(
        self,
        *,
        v0: float,
        t: int,
        t_steps: int,
        T: float,
        T_target: float,
        rng: np.random.Generator,
    ) -> float:
        v_new = float(v0 + rng.normal(0.0, self.sigma))
        return float(np.clip(v_new, self.v0_min, self.v0_max))
