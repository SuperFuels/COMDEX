# /workspaces/COMDEX/backend/modules/aion_equities/feeds/fx_quarter_average_store.py
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.modules.aion_equities.feeds.fx_ewma import EWMARunner, alpha_from_half_life


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _parse_iso_date(value: str) -> date:
    s = str(value or "").strip()
    if not s:
        raise ValueError("empty date")
    # accept "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SSZ"
    s = s[:10]
    return date.fromisoformat(s)


def _quarter_bounds(fiscal_period_ref: str) -> Tuple[date, date]:
    """
    Assumes fiscal_period_ref is calendar quarter: YYYY-Q#
    Returns (start_date, end_date_inclusive).
    """
    s = str(fiscal_period_ref or "").strip()
    if len(s) != 7 or s[4] != "-" or s[5] != "Q":
        raise ValueError(f"Invalid fiscal_period_ref: {fiscal_period_ref!r} (expected YYYY-Q#)")
    year = int(s[:4])
    q = int(s[6])
    if q not in (1, 2, 3, 4):
        raise ValueError(f"Invalid quarter in fiscal_period_ref: {fiscal_period_ref!r}")

    if q == 1:
        start = date(year, 1, 1)
        end = date(year, 3, 31)
    elif q == 2:
        start = date(year, 4, 1)
        end = date(year, 6, 30)
    elif q == 3:
        start = date(year, 7, 1)
        end = date(year, 9, 30)
    else:
        start = date(year, 10, 1)
        end = date(year, 12, 31)
    return start, end


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


@dataclass
class FXQuarterAvgResult:
    spot: float
    running_avg: float
    ewma_avg: float
    sample_count: int


class FXQuarterAverageStore:
    """
    Stores daily samples per feed_id per fiscal_period_ref, and computes:
      - running_avg: simple mean of daily samples
      - ewma_avg: EWMA over daily samples (half-life configurable)

    Disk layout:
      <base_dir>/fx_quarter_avg/<feed_id>/<fiscal_period_ref>.json
    """

    def __init__(
        self,
        *,
        base_dir: str | Path,
        half_life_days: float = 10.0,
    ):
        self.base_dir = Path(base_dir)
        self.root = self.base_dir / "fx_quarter_avg"
        self.root.mkdir(parents=True, exist_ok=True)
        self.half_life_days = float(half_life_days)
        self.alpha = alpha_from_half_life(self.half_life_days)

    def _path(self, feed_id: str, fiscal_period_ref: str) -> Path:
        return self.root / _safe_segment(feed_id) / f"{_safe_segment(fiscal_period_ref)}.json"

    def _load(self, feed_id: str, fiscal_period_ref: str) -> Dict[str, Any]:
        p = self._path(feed_id, fiscal_period_ref)
        if not p.exists():
            return {
                "feed_id": str(feed_id),
                "fiscal_period_ref": str(fiscal_period_ref),
                "samples": {},  # "YYYY-MM-DD" -> float
                "running_sum": 0.0,
                "running_count": 0,
                "ewma": {"alpha": self.alpha, "value": None},
                "updated_at": None,
            }
        return json.loads(p.read_text(encoding="utf-8"))

    def _write(self, feed_id: str, fiscal_period_ref: str, payload: Dict[str, Any]) -> None:
        p = self._path(feed_id, fiscal_period_ref)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def update(
        self,
        *,
        feed_id: str,
        fiscal_period_ref: str,
        as_of: str,
        spot_value: float,
    ) -> FXQuarterAvgResult:
        start, end = _quarter_bounds(fiscal_period_ref)
        d = _parse_iso_date(as_of)
        if d < start or d > end:
            # out of period; do NOT poison averages
            raise ValueError(
                f"as_of {d.isoformat()} outside {fiscal_period_ref} bounds {start.isoformat()}..{end.isoformat()}"
            )

        state = self._load(feed_id, fiscal_period_ref)

        samples: Dict[str, Any] = state.get("samples") if isinstance(state.get("samples"), dict) else {}
        key = d.isoformat()

        prev = _safe_float(samples.get(key))
        spot = float(spot_value)

        # maintain running sum/count without re-summing whole dict
        running_sum = float(state.get("running_sum") or 0.0)
        running_count = int(state.get("running_count") or 0)

        if prev is None:
            samples[key] = spot
            running_sum += spot
            running_count += 1
        else:
            # overwrite same-day sample
            samples[key] = spot
            running_sum = running_sum - prev + spot

        # EWMA
        ewma_state = state.get("ewma") if isinstance(state.get("ewma"), dict) else {}
        alpha = float(ewma_state.get("alpha") or self.alpha)
        runner = EWMARunner(alpha=alpha, value=_safe_float(ewma_state.get("value")))
        ewma_val = float(runner.update(spot))

        running_avg = (running_sum / running_count) if running_count > 0 else spot

        state["samples"] = samples
        state["running_sum"] = running_sum
        state["running_count"] = running_count
        state["ewma"] = {"alpha": alpha, "value": ewma_val}
        state["updated_at"] = as_of

        self._write(feed_id, fiscal_period_ref, state)

        return FXQuarterAvgResult(
            spot=spot,
            running_avg=float(running_avg),
            ewma_avg=float(ewma_val),
            sample_count=int(running_count),
        )

    def load_summary(self, *, feed_id: str, fiscal_period_ref: str) -> Dict[str, Any]:
        state = self._load(feed_id, fiscal_period_ref)
        # safe summary only
        return {
            "feed_id": state.get("feed_id"),
            "fiscal_period_ref": state.get("fiscal_period_ref"),
            "running_count": state.get("running_count"),
            "running_sum": state.get("running_sum"),
            "ewma": deepcopy(state.get("ewma")),
            "updated_at": state.get("updated_at"),
        }


__all__ = ["FXQuarterAverageStore", "FXQuarterAvgResult"]