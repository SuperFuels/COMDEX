from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class PIConfig:
    steps: int = 200
    dt: float = 0.05
    seed: int = 1

    # plant
    drive: float = 1.0
    alpha0: float = 0.5
    noise_sigma: float = 0.0

    # bounds
    alpha_min: float = 0.05
    alpha_max: float = 2.0

    # protocol tag
    tups_version: str = "TUPS_V1.2"

    def to_dict(self) -> dict:
        return asdict(self)
