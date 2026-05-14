# /workspaces/COMDEX/backend/modules/aion_equities/trading/expected_value.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


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
            s = s.replace("%", "").strip()
            return float(s)
        return float(x)
    except Exception:
        return None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class EVInputs:
    """
    All probabilities expressed as 0..1.
    Gain/loss expressed as percent moves (e.g., +18 means +18%).
    """
    probability_confirm: float
    probability_break: float
    expected_gain_pct: float
    expected_loss_pct: float  # can be positive or negative; internally treated as magnitude
    conviction_score: Optional[float] = None  # 0..1 optional


@dataclass(frozen=True)
class EVResult:
    expected_value_pct: float
    kelly_full_fraction: float
    kelly_scaled_fraction: float
    suggested_size_percent: float

    # Diagnostics
    kelly_scale: float
    max_size_percent_cap: float
    inputs: EVInputs


class ExpectedValueCalculator:
    """
    EV:
      EV_pct = p_confirm * gain_pct - p_break * loss_pct

    Kelly (fraction of capital):
      b = gain/loss
      f_full = (b*p - q)/b
      f_scaled = clamp(f_full * kelly_scale, 0..1)
      suggested_size_percent = min(max_size_percent, f_scaled * 100)

    Notes:
      - Uses loss magnitude (abs).
      - Optionally multiplies Kelly by conviction_score (0..1) if provided.
    """

    def __init__(
        self,
        *,
        kelly_scale: float = 0.5,      # half-Kelly default
        max_size_percent: float = 25.0 # hard cap
    ):
        self.kelly_scale = float(kelly_scale)
        self.max_size_percent = float(max_size_percent)

    def compute(self, inp: EVInputs) -> EVResult:
        p = _clamp(float(inp.probability_confirm), 0.0, 1.0)
        q = _clamp(float(inp.probability_break), 0.0, 1.0)
        g = float(inp.expected_gain_pct)
        l = abs(float(inp.expected_loss_pct))

        if g <= 0.0:
            raise ValueError("expected_gain_pct must be > 0")
        if l <= 0.0:
            raise ValueError("expected_loss_pct must be non-zero")

        ev_pct = (p * g) - (q * l)

        b = g / l
        f_full = ((b * p) - q) / b

        if inp.conviction_score is not None:
            f_full *= _clamp(float(inp.conviction_score), 0.0, 1.0)

        f_scaled = _clamp(f_full * self.kelly_scale, 0.0, 1.0)
        suggested_size_percent = min(self.max_size_percent, f_scaled * 100.0)

        return EVResult(
            expected_value_pct=float(ev_pct),
            kelly_full_fraction=float(f_full),
            kelly_scaled_fraction=float(f_scaled),
            suggested_size_percent=float(suggested_size_percent),
            kelly_scale=float(self.kelly_scale),
            max_size_percent_cap=float(self.max_size_percent),
            inputs=inp,
        )

    # -----------------------------
    # Convenience: accept dicts
    # -----------------------------
    def compute_from_dict(self, d: Dict[str, Any]) -> Optional[EVResult]:
        """
        Best-effort: returns None if any required input is missing/unparseable.
        Expected keys (aliases tolerated):
          probability_confirm / p_confirm
          probability_break / p_break
          expected_gain_pct / expected_upside_pct
          expected_loss_pct / expected_downside_pct
          conviction_score (optional)
        """
        p_confirm = _as_float(d.get("probability_confirm") if "probability_confirm" in d else d.get("p_confirm"))
        p_break = _as_float(d.get("probability_break") if "probability_break" in d else d.get("p_break"))
        gain_pct = _as_float(d.get("expected_gain_pct") if "expected_gain_pct" in d else d.get("expected_upside_pct"))
        loss_pct = _as_float(d.get("expected_loss_pct") if "expected_loss_pct" in d else d.get("expected_downside_pct"))
        conviction = _as_float(d.get("conviction_score"))

        if p_confirm is None or p_break is None or gain_pct is None or loss_pct is None:
            return None

        try:
            return self.compute(
                EVInputs(
                    probability_confirm=float(p_confirm),
                    probability_break=float(p_break),
                    expected_gain_pct=float(gain_pct),
                    expected_loss_pct=float(loss_pct),
                    conviction_score=float(conviction) if conviction is not None else None,
                )
            )
        except Exception:
            return None