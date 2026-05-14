# backend/modules/aion_equities/trading/position_sizing.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


def _as_float(x: Any, *, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None or isinstance(x, bool):
            return default
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            s = x.strip()
            if not s:
                return default
            s = s.replace("%", "").strip()
            return float(s)
        return float(x)
    except Exception:
        return default


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class PositionSizingInputs:
    """
    Probabilities are 0..1.
    exp_gain/exp_loss are percent moves (e.g. +18 means +18%).
    Returned size is a fraction of portfolio (0..max_position_fraction).
    """
    p_confirm: float
    p_break: float
    exp_gain: float
    exp_loss: float

    conviction: float = 1.0               # 0..1
    kelly_fraction: float = 0.25          # e.g. 0.5 (half Kelly) or 0.25 (quarter Kelly)
    max_position_fraction: float = 0.10   # e.g. 0.10 => 10% cap


def modified_kelly_size(x: PositionSizingInputs) -> float:
    """
    Modified Kelly with cap + conviction scaling.

    Kelly:
      b = gain/loss
      f* = (b*p - q) / b

    Modified:
      size = clamp( conviction * kelly_fraction * max(0, f*), 0, max_position_fraction )

    Notes:
      - exp_loss uses magnitude (abs) to avoid sign ambiguity.
      - requires p_confirm + p_break <= 1.0 (rest = "other/neutral" outcomes).
    """
    p = _clamp(float(x.p_confirm), 0.0, 1.0)
    q = _clamp(float(x.p_break), 0.0, 1.0)

    if p + q > 1.0 + 1e-9:
        raise ValueError("p_confirm + p_break must be <= 1.0")

    conviction = _clamp(float(x.conviction), 0.0, 1.0)
    kelly_fraction = float(x.kelly_fraction)
    if kelly_fraction < 0.0:
        raise ValueError("kelly_fraction must be >= 0")

    cap = float(x.max_position_fraction)
    if cap < 0.0:
        raise ValueError("max_position_fraction must be >= 0")

    gain = float(x.exp_gain)
    loss = abs(float(x.exp_loss))

    if gain <= 0.0 or loss <= 0.0 or cap == 0.0 or conviction == 0.0 or kelly_fraction == 0.0:
        return 0.0

    b = gain / loss
    if b <= 0.0:
        return 0.0

    f_star = ((b * p) - q) / b  # full Kelly fraction
    f_star = max(0.0, f_star)

    sized = conviction * kelly_fraction * f_star
    return _clamp(sized, 0.0, cap)


def modified_kelly_size_percent(x: PositionSizingInputs) -> float:
    """Convenience: returns size as percent (0..cap*100)."""
    return modified_kelly_size(x) * 100.0


def sizing_from_dict(d: dict[str, Any]) -> float:
    """
    Best-effort helper for wiring into existing packets.
    Accepts aliases:
      p_confirm/probability_confirm
      p_break/probability_break
      exp_gain/expected_gain_pct/expected_upside_pct
      exp_loss/expected_loss_pct/expected_downside_pct
      conviction/conviction_score
      kelly_fraction/kelly_scale (if kelly_scale is 0.5, pass kelly_fraction=0.5)
      max_position_fraction/max_position_pct (pct interpreted as 0..100)
    Returns fraction of portfolio.
    """
    p_confirm = _as_float(d.get("p_confirm", d.get("probability_confirm")))
    p_break = _as_float(d.get("p_break", d.get("probability_break")))
    exp_gain = _as_float(d.get("exp_gain", d.get("expected_gain_pct", d.get("expected_upside_pct"))))
    exp_loss = _as_float(d.get("exp_loss", d.get("expected_loss_pct", d.get("expected_downside_pct"))))

    if p_confirm is None or p_break is None or exp_gain is None or exp_loss is None:
        return 0.0

    conviction = _as_float(d.get("conviction", d.get("conviction_score")), default=1.0) or 1.0

    kf = _as_float(d.get("kelly_fraction"), default=None)
    if kf is None:
        # tolerate naming drift: some configs call this "kelly_scale" meaning "use half/quarter Kelly"
        kf = _as_float(d.get("kelly_scale"), default=0.25) or 0.25

    cap = _as_float(d.get("max_position_fraction"), default=None)
    if cap is None:
        cap_pct = _as_float(d.get("max_position_pct"), default=None)
        cap = (cap_pct / 100.0) if cap_pct is not None else 0.10

    return modified_kelly_size(
        PositionSizingInputs(
            p_confirm=float(p_confirm),
            p_break=float(p_break),
            exp_gain=float(exp_gain),
            exp_loss=float(exp_loss),
            conviction=float(conviction),
            kelly_fraction=float(kf),
            max_position_fraction=float(cap),
        )
    )