# /workspaces/COMDEX/backend/modules/aion_equities/portfolio/drawdown.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or isinstance(x, bool):
            return float(default)
        return float(x)
    except Exception:
        return float(default)


@dataclass
class DrawdownState:
    """
    Tracks peak-to-trough drawdown for a single series (price or NAV).

    - peak: highest observed value
    - trough: lowest value observed since peak
    - drawdown_pct: (value - peak) / peak  (negative or 0)
    - max_drawdown_pct: most negative drawdown observed historically
    """
    peak: float | None = None
    trough: float | None = None
    drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    peak_as_of: Optional[str] = None
    trough_as_of: Optional[str] = None
    last_value: float | None = None
    last_as_of: Optional[str] = None

    def update(self, value: float, *, as_of: Optional[str] = None) -> Dict[str, Any]:
        v = float(value)

        # initialize
        if self.peak is None:
            self.peak = v
            self.trough = v
            self.drawdown_pct = 0.0
            self.max_drawdown_pct = 0.0
            self.peak_as_of = as_of
            self.trough_as_of = as_of
        else:
            assert self.peak is not None

            # new peak resets trough
            if v > self.peak:
                self.peak = v
                self.peak_as_of = as_of
                self.trough = v
                self.trough_as_of = as_of
                self.drawdown_pct = 0.0
            else:
                # update trough
                if self.trough is None or v < self.trough:
                    self.trough = v
                    self.trough_as_of = as_of

                # compute drawdown
                if self.peak > 0:
                    self.drawdown_pct = (v - self.peak) / self.peak
                else:
                    self.drawdown_pct = 0.0

                # update max drawdown (more negative is worse)
                if self.drawdown_pct < self.max_drawdown_pct:
                    self.max_drawdown_pct = self.drawdown_pct

        self.last_value = v
        self.last_as_of = as_of

        return {
            "peak": self.peak,
            "trough": self.trough,
            "drawdown_pct": self.drawdown_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "peak_as_of": self.peak_as_of,
            "trough_as_of": self.trough_as_of,
            "last_value": self.last_value,
            "last_as_of": self.last_as_of,
        }


def compute_drawdown_pct(value: float, peak: float) -> float:
    v = float(value)
    p = float(peak)
    if p <= 0:
        return 0.0
    return (v - p) / p


def drawdown_breached(
    *,
    drawdown_pct: float,
    breach_threshold_pct: float,
) -> bool:
    """
    breach_threshold_pct is expressed as a POSITIVE percent, e.g. 0.12 for -12%.
    Returns True if drawdown is <= -breach_threshold_pct.
    """
    dd = float(drawdown_pct)
    thr = float(breach_threshold_pct)
    if thr < 0:
        raise ValueError("breach_threshold_pct must be >= 0")
    return dd <= -thr


__all__ = [
    "DrawdownState",
    "compute_drawdown_pct",
    "drawdown_breached",
]