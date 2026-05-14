from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# -----------------------------
# MG01: kappa controllers
# -----------------------------
@dataclass
class FluxHoldController:
    """Closed-loop controller for kappa ("flux grip")."""

    lr: float = 0.60
    kappa_min: float = 0.0
    kappa_max: float = 3.0
    name: str = "tessaris_flux_hold"

    def step(self, *, kappa: float, angle_err: float, t: int, rng: np.random.Generator) -> float:
        target_err = 0.05
        err = float(angle_err - target_err)

        k_new = float(kappa + self.lr * err)
        k_new = 0.990 * k_new + 0.010 * float(kappa)  # smooth

        return float(np.clip(k_new, self.kappa_min, self.kappa_max))


@dataclass
class RandomJitterKappaController:
    """Baseline: random jitter on kappa (no feedback)."""

    sigma: float = 0.60
    kappa_min: float = 0.0
    kappa_max: float = 3.0
    name: str = "random_jitter_kappa"

    def step(self, *, kappa: float, angle_err: float, t: int, rng: np.random.Generator) -> float:
        k_new = float(kappa + rng.normal(0.0, self.sigma))
        return float(np.clip(k_new, self.kappa_min, self.kappa_max))


# -----------------------------
# MG02: gamma controllers
# -----------------------------
@dataclass
class ContainmentGammaHoldController:
    """
    Closed-loop containment controller for gamma.

    Key property for audit stability:
      - gamma never collapses to 0 (gamma_floor), so "tess" is not identical to open-loop.
      - gamma increases when leak > target_leak.
      - gamma relaxes toward gamma_floor when leak <= target.
    """
    lr: float = 3.0
    target_leak: float = 0.006
    gamma_floor: float = 0.60
    gamma_min: float = 0.0
    gamma_max: float = 6.0
    name: str = "tessaris_gamma_hold"

    def step(self, *, gamma: float, leak: float, t: int, rng: np.random.Generator) -> float:
        leak = float(leak)

        if leak > self.target_leak:
            # push gamma up if leaking
            err = leak - self.target_leak
            g_new = float(gamma + self.lr * err)
        else:
            # relax toward floor (not toward 0)
            g_new = float(0.995 * gamma + 0.005 * self.gamma_floor)

        # enforce floor before clamp
        g_new = max(g_new, float(self.gamma_floor))
        g_new = float(np.clip(g_new, self.gamma_min, self.gamma_max))
        return g_new


@dataclass
class RandomJitterGammaController:
    """Baseline: random jitter on gamma (no feedback)."""

    sigma: float = 0.80
    gamma_min: float = 0.0
    gamma_max: float = 6.0
    name: str = "random_jitter_gamma"

    def step(self, *, gamma: float, leak: float, t: int, rng: np.random.Generator) -> float:
        g_new = float(gamma + rng.normal(0.0, self.sigma))
        return float(np.clip(g_new, self.gamma_min, self.gamma_max))
