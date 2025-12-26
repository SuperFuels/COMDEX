from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class OpenLoopController:
    """
    Baseline: no control (gain = 0).
    """
    name: str = "open_loop"

    def reset(self, seed: int) -> None:
        pass

    def step(self, obs: dict) -> float:
        return 0.0


@dataclass
class RandomJitterGainController:
    """
    Baseline: random gain jitter in [0, gain_cap].
    """
    gain_cap: float = 0.25
    name: str = "random_jitter_gain"

    _rng: np.random.Generator | None = None

    def reset(self, seed: int) -> None:
        self._rng = np.random.default_rng(seed)

    def step(self, obs: dict) -> float:
        assert self._rng is not None
        return float(self._rng.uniform(0.0, self.gain_cap))


@dataclass
class TessarisSolitonHoldController:
    """
    Closed-loop: raise gain when width/peak deviate from target.

    Parameters match your test call:
      base_gain, kp_width, kp_peak, gain_cap, chi_cap
    """
    base_gain: float = 0.02
    kp_width: float = 0.004
    kp_peak: float = 0.004
    gain_cap: float = 0.25
    chi_cap: float = 2.0
    name: str = "tessaris_soliton_hold"

    def reset(self, seed: int) -> None:
        pass

    def step(self, obs: dict) -> float:
        w = float(obs["width"])
        a = float(obs["peak"])
        w0 = float(obs["width0"])
        a0 = float(obs["peak0"])

        # errors as % (dimensionless)
        ew = (w - w0) / max(1e-9, w0)
        ea = (a0 - a) / max(1e-9, a0)

        gain = self.base_gain + self.kp_width * abs(ew * 100.0) + self.kp_peak * abs(ea * 100.0)
        if gain < 0.0:
            gain = 0.0
        if gain > self.gain_cap:
            gain = self.gain_cap
        return float(gain)
