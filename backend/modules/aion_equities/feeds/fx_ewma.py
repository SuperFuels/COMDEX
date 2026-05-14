# backend/modules/aion_equities/feeds/fx_ewma.py
from __future__ import annotations

from dataclasses import dataclass
from math import pow
from typing import Any, Optional


def alpha_from_half_life_days(half_life_days: float) -> float:
    """
    Convert half-life (in days) to EWMA alpha.

    Half-life definition:
      After 'half_life_days' updates, the weight of a single observation decays by 50%.

    alpha = 1 - 0.5^(1/half_life_days)
    """
    hl = float(half_life_days)
    if hl <= 0.0:
        raise ValueError("half_life_days must be > 0")
    a = 1.0 - pow(0.5, 1.0 / hl)
    # guard against float weirdness
    if not (0.0 < a <= 1.0):
        raise ValueError("computed alpha out of range")
    return a


def alpha_from_half_life(half_life_days: float) -> float:
    """Backward-compat alias."""
    return alpha_from_half_life_days(half_life_days)


def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None or isinstance(x, bool):
            return None
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            s = x.strip()
            if not s:
                return None
            return float(s)
        return float(x)
    except Exception:
        return None


@dataclass
class EWMARunner:
    """
    Simple EWMA runner.

    Typical usage for FX:
      - feed daily ECB spot rates into update()
      - use value as "EWMA spot"
      - compute "EWMA quarterly avg" by aggregating EWMA values across the quarter
        (or keep a separate quarter accumulator if you want true "EWMA of daily rates")

    Notes:
      - alpha in (0, 1]
      - if allow_missing=True, update(None) is a no-op (returns current value)
    """
    alpha: float
    value: float | None = None
    allow_missing: bool = True

    def __post_init__(self) -> None:
        a = float(self.alpha)
        if not (0.0 < a <= 1.0):
            raise ValueError("alpha must be in (0, 1]")
        object.__setattr__(self, "alpha", a)

    def reset(self) -> None:
        object.__setattr__(self, "value", None)

    def update(self, x: Any) -> float | None:
        """
        Update the EWMA with a new observation.

        Returns:
          - updated EWMA value (float)
          - or None if value is None and x is missing and allow_missing=True
        """
        fx = _as_float(x)
        if fx is None:
            if self.allow_missing:
                return self.value
            raise ValueError("missing/invalid observation")

        if self.value is None:
            object.__setattr__(self, "value", float(fx))
        else:
            new_v = (self.alpha * float(fx)) + ((1.0 - self.alpha) * float(self.value))
            object.__setattr__(self, "value", new_v)

        return self.value

    def update_or_raise(self, x: Any) -> float:
        """Strict variant: raises if x is missing/invalid and returns float."""
        prev_allow = self.allow_missing
        object.__setattr__(self, "allow_missing", False)
        try:
            v = self.update(x)
            assert v is not None
            return float(v)
        finally:
            object.__setattr__(self, "allow_missing", prev_allow)


__all__ = [
    "alpha_from_half_life_days",
    "alpha_from_half_life",
    "EWMARunner",
]