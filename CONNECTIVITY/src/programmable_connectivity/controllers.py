from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .ops import clip

@dataclass
class SigmaHoldController:
    """Deterministic Sigma-control: hold sigma at a constant value."""
    name: str = "tessaris_sigma_hold"
    sigma: float = 1.0

    def reset(self) -> None:
        pass

    def step(self, *, C: float, t: int, rng: np.random.Generator) -> float:
        return clip(self.sigma, 0.0, 1.0)

@dataclass
class OpenLoopController:
    """Open-loop: sigma=0, i.e., no throat coupling."""
    name: str = "open_loop"

    def reset(self) -> None:
        pass

    def step(self, *, C: float, t: int, rng: np.random.Generator) -> float:
        return 0.0

@dataclass
class RandomJitterSigmaController:
    """Random jitter baseline on sigma (bounded 0..1). Deterministic via seed."""
    name: str = "random_jitter_sigma"
    sigma0: float = 0.5
    sigma_step: float = 0.10

    def reset(self) -> None:
        self._sigma = float(self.sigma0)

    def step(self, *, C: float, t: int, rng: np.random.Generator) -> float:
        self._sigma = clip(self._sigma + float(rng.normal(0.0, self.sigma_step)), 0.0, 1.0)
        return self._sigma
