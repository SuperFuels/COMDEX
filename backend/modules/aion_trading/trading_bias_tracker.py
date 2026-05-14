# /workspaces/COMDEX/backend/modules/aion_trading/trading_bias_tracker.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


BIAS_TRACKER_SCHEMA_VERSION = "aion.trading.daily_bias_tracker.v1"


@dataclass
class DailyBiasRecord:
    trading_date: str                      # YYYY-MM-DD
    instrument: str                        # e.g. EUR/USD
    dmip_checkpoint: str                   # pre_market / london_open / ...
    predicted_bias: str                    # bullish / bearish / neutral
    actual_day_direction: Optional[str]    # bullish / bearish / neutral, set at EOD
    bias_correct: Optional[bool]           # None until EOD
    confidence: Optional[float] = None
    decision_event_id: Optional[str] = None
    decision_snapshot_hash: Optional[str] = None
    notes: Optional[str] = None


def score_bias_correct(predicted_bias: str, actual_day_direction: str) -> Optional[bool]:
    p = str(predicted_bias or "").strip().lower()
    a = str(actual_day_direction or "").strip().lower()
    if p not in {"bullish", "bearish", "neutral"}:
        return None
    if a not in {"bullish", "bearish", "neutral"}:
        return None
    return p == a


def build_bias_tracker_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = 0
    resolved = 0
    correct = 0
    by_instrument: Dict[str, Dict[str, int]] = {}

    for r in records or []:
        if not isinstance(r, dict):
            continue
        total += 1
        inst = str(r.get("instrument") or "UNKNOWN")
        bucket = by_instrument.setdefault(inst, {"total": 0, "resolved": 0, "correct": 0})
        bucket["total"] += 1

        bc = r.get("bias_correct")
        if bc in (True, False):
            resolved += 1
            bucket["resolved"] += 1
            if bc is True:
                correct += 1
                bucket["correct"] += 1

    accuracy = (correct / resolved) if resolved > 0 else None

    return {
        "schema_version": BIAS_TRACKER_SCHEMA_VERSION,
        "total_records": total,
        "resolved_records": resolved,
        "correct_records": correct,
        "accuracy": round(accuracy, 6) if accuracy is not None else None,
        "by_instrument": {
            k: {
                **v,
                "accuracy": round(v["correct"] / v["resolved"], 6) if v["resolved"] > 0 else None
            }
            for k, v in sorted(by_instrument.items())
        },
    }