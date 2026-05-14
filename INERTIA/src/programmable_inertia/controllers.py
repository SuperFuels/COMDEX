from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class AlphaHoldController:
    """
    Simple closed-loop alpha controller:
      - if v < v_target => decrease alpha (less damping) => higher terminal velocity
      - if v > v_target => increase alpha (more damping)
    """
    lr: float = 0.02
    max_delta: float = 0.02
    alpha_min: float = 0.05
    alpha_max: float = 2.0
    name: str = "tessaris_alpha_hold"

    def step(self, *, alpha: float, v: float, v_target: float, t: int, rng: np.random.Generator) -> float:
        err = (v_target - v)
        delta = float(np.clip(self.lr * err, -self.max_delta, self.max_delta))
        a2 = float(np.clip(alpha - delta, self.alpha_min, self.alpha_max))
        return a2


@dataclass
class RandomJitterAlphaController:
    sigma: float = 0.05
    alpha_min: float = 0.05
    alpha_max: float = 2.0
    name: str = "random_jitter_alpha"

    def step(self, *, alpha: float, v: float, v_target: float, t: int, rng: np.random.Generator) -> float:
        a2 = float(alpha + rng.normal(0.0, self.sigma))
        return float(np.clip(a2, self.alpha_min, self.alpha_max))
