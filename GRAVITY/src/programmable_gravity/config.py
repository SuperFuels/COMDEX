from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class PGConfig:
    N: int = 128
    steps: int = 80
    seed: int = 1
    drift_sigma: float = 1e-3

    # Target well parameters (entropy well -> curvature target via Laplacian)
    well_sigma: float = 10.0
    well_amp: float = 1.0

    # bookkeeping
    tups_version: str = "TUPS_V1.2"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
