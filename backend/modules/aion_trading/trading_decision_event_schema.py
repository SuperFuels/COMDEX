# /workspaces/COMDEX/backend/modules/aion_trading/trading_decision_event_schema.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


DECISION_EVENT_SCHEMA_VERSION = "aion.trading.decision_event.v1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TradingDecisionEventValidation:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def build_trading_decision_event(
    *,
    session_id: str,
    event_type: str,  # e.g. dmip_bias, risk_validation, trade_candidate_decision
    instrument: str,
    timeframe: Optional[str],
    side_bias: Optional[str],  # bullish/bearish/neutral
    decision: Dict[str, Any],
    decision_influence_snapshot_hash: str,
    process_score: Dict[str, Any],
    outcome_score: Optional[Dict[str, Any]] = None,
    features: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    process_score = {
      "quality": 0.0..1.0,
      "confidence": 0.0..1.0,
      "checklist_pass_rate": 0.0..1.0,
      "violations": ["..."],
      "notes": "..."
    }

    outcome_score (optional until known later) = {
      "status": "pending|win|loss|scratch|invalidated",
      "pnl_r": float | None,
      "mae_r": float | None,
      "mfe_r": float | None,
      "bias_correct": bool | None,
      "scored_at": iso str | None
    }
    """
    return {
        "schema_version": DECISION_EVENT_SCHEMA_VERSION,
        "event_id": None,  # let storage assign if desired
        "timestamp": _utc_now_iso(),
        "session_id": session_id,
        "event_type": event_type,
        "instrument": instrument,
        "timeframe": timeframe,
        "side_bias": side_bias,
        "decision": decision or {},
        "decision_influence": {
            "snapshot_hash": decision_influence_snapshot_hash,
        },
        "process_score": process_score or {},
        "outcome_score": outcome_score,  # may be None / pending
        "features": features or {},
        "metadata": metadata or {},
    }


def validate_trading_decision_event(event: Dict[str, Any]) -> TradingDecisionEventValidation:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(event, dict):
        return TradingDecisionEventValidation(ok=False, errors=["event_not_dict"])

    if event.get("schema_version") != DECISION_EVENT_SCHEMA_VERSION:
        errors.append("unsupported_schema_version")

    for k in ["timestamp", "session_id", "event_type", "instrument", "decision", "decision_influence", "process_score"]:
        if k not in event:
            errors.append(f"missing_required:{k}")

    di = event.get("decision_influence") or {}
    if not isinstance(di, dict) or not di.get("snapshot_hash"):
        errors.append("missing_decision_influence_snapshot_hash")

    ps = event.get("process_score")
    if not isinstance(ps, dict):
        errors.append("process_score_not_dict")
    else:
        # Explicit from day one
        for k in ["quality", "confidence"]:
            if k not in ps:
                errors.append(f"missing_process_score_field:{k}")
        for k in ["quality", "confidence", "checklist_pass_rate"]:
            if k in ps and ps.get(k) is not None:
                try:
                    fv = float(ps[k])
                    if fv < 0.0 or fv > 1.0:
                        errors.append(f"process_score_out_of_range:{k}")
                except Exception:
                    errors.append(f"process_score_not_numeric:{k}")

    os_ = event.get("outcome_score")
    if os_ is not None:
        if not isinstance(os_, dict):
            errors.append("outcome_score_not_dict")
        else:
            status = os_.get("status")
            if status not in {None, "pending", "win", "loss", "scratch", "invalidated"}:
                errors.append("outcome_score_invalid_status")
            if "bias_correct" in os_ and os_["bias_correct"] not in {None, True, False}:
                errors.append("outcome_score_invalid_bias_correct")

    return TradingDecisionEventValidation(ok=(len(errors) == 0), errors=errors, warnings=warnings)