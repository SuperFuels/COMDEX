from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import time
import uuid


def _now_ts() -> float:
    return time.time()


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _norm_key(s: Any) -> str:
    return str(s or "").strip()


@dataclass
class TradingLearningEvent:
    event_id: str
    event_type: str  # "dmip_checkpoint" | "risk_validation"
    created_at: float
    session_id: str
    turn_id: str
    skill_id: str
    ok: bool
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "created_at": self.created_at,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "skill_id": self.skill_id,
            "ok": bool(self.ok),
            "payload": dict(self.payload or {}),
        }


class TradingLearningCaptureRuntime:
    """
    In-memory Sprint 3 trading learning capture (paper-only).
    Non-breaking and intentionally simple. Can later be backed by a persistent store.
    """

    def __init__(self) -> None:
        self._events: List[TradingLearningEvent] = []

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_dmip_checkpoint_event(
        self,
        *,
        session_id: str,
        turn_id: str,
        skill_id: str,
        skill_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        out = dict(skill_output or {})

        checkpoint = str(out.get("checkpoint") or out.get("dmip_checkpoint") or "unknown")
        ok = bool(out.get("ok", True))

        # Try common result shapes
        bias_sheet = dict(out.get("bias_sheet") or {})
        if not bias_sheet:
            bias_sheet = dict((out.get("result") or {}).get("bias_sheet") or {})

        pair_bias = dict(bias_sheet.get("pair_bias") or {})
        if not pair_bias:
            # fallback for simple scaffolds
            pair_bias = dict(out.get("pair_bias") or {})

        payload = {
            "checkpoint": checkpoint,
            "pair_bias": pair_bias,
            "trading_confidence": str(
                bias_sheet.get("trading_confidence")
                or out.get("trading_confidence")
                or "unknown"
            ),
            "risk_environment": str(
                bias_sheet.get("risk_environment")
                or out.get("risk_environment")
                or "unknown"
            ),
            "stand_down": bool(
                out.get("stand_down", False)
                or (str(bias_sheet.get("trading_confidence") or "").upper() == "STAND DOWN")
            ),
        }

        ev = TradingLearningEvent(
            event_id=str(uuid.uuid4()),
            event_type="dmip_checkpoint",
            created_at=_now_ts(),
            session_id=str(session_id),
            turn_id=str(turn_id),
            skill_id=str(skill_id),
            ok=ok,
            payload=payload,
        )
        self._events.append(ev)
        return ev.to_dict()

    def log_risk_validation_event(
        self,
        *,
        session_id: str,
        turn_id: str,
        skill_id: str,
        skill_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        out = dict(skill_output or {})
        ok = bool(out.get("ok", False))

        result = dict(out.get("result") or {})
        proposal = dict(out.get("proposal") or {})

        violations = list(result.get("violations") or [])
        rr = _safe_float(
            result.get("risk_reward_ratio", result.get("rr", result.get("rr_ratio"))),
            0.0,
        )

        payload = {
            "pair": str(proposal.get("pair") or ""),
            "strategy_tier": str(proposal.get("strategy_tier") or ""),
            "direction": str(proposal.get("direction") or ""),
            "account_mode": str(proposal.get("account_mode") or ""),
            "risk_pct": _safe_float(proposal.get("risk_pct"), 0.0),
            "stop_pips": _safe_float(proposal.get("stop_pips"), 0.0),
            "rr": rr,
            "violations": [str(v) for v in violations],
            "violation_count": len(violations),
        }

        ev = TradingLearningEvent(
            event_id=str(uuid.uuid4()),
            event_type="risk_validation",
            created_at=_now_ts(),
            session_id=str(session_id),
            turn_id=str(turn_id),
            skill_id=str(skill_id),
            ok=ok,
            payload=payload,
        )
        self._events.append(ev)
        return ev.to_dict()

    # ------------------------------------------------------------------
    # Read APIs
    # ------------------------------------------------------------------

    def list_events(
        self,
        *,
        event_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        rows = self._events
        if event_type:
            et = str(event_type)
            rows = [e for e in rows if e.event_type == et]
        if limit is not None and limit >= 0:
            rows = rows[-int(limit):]
        return [e.to_dict() for e in rows]

    def clear(self) -> None:
        self._events.clear()

    # ------------------------------------------------------------------
    # Sprint 3 weakness signals
    # ------------------------------------------------------------------

    def build_weakness_signals(self) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []

        # 1) Risk validation violation frequency
        risk_events = [e for e in self._events if e.event_type == "risk_validation"]
        violation_counts: Dict[str, int] = {}
        low_rr_count = 0
        repeated_invalid_count = 0

        for e in risk_events:
            p = e.payload or {}
            violations = list(p.get("violations") or [])
            rr = _safe_float(p.get("rr"), 0.0)

            if not e.ok:
                repeated_invalid_count += 1

            if rr > 0 and rr < 2.0:
                low_rr_count += 1

            for v in violations:
                k = _norm_key(v)
                if not k:
                    continue
                violation_counts[k] = violation_counts.get(k, 0) + 1

        for rule, count in sorted(violation_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            if count >= 2:
                signals.append(
                    {
                        "kind": "trading_risk_violation_frequency",
                        "severity": "medium" if count < 5 else "high",
                        "rule": rule,
                        "count": count,
                        "message": f"Repeated risk validation violation: {rule} ({count}x).",
                    }
                )

        if low_rr_count >= 2:
            signals.append(
                {
                    "kind": "trading_low_rr_proposals",
                    "severity": "medium",
                    "count": low_rr_count,
                    "message": f"Recurring low risk/reward proposals detected ({low_rr_count}x, RR<2.0).",
                }
            )

        if repeated_invalid_count >= 3:
            signals.append(
                {
                    "kind": "trading_repeated_invalid_proposals",
                    "severity": "high",
                    "count": repeated_invalid_count,
                    "message": f"Repeated invalid trade proposals detected ({repeated_invalid_count}x).",
                }
            )

        # 2) DMIP stand-down / avoid clustering
        dmip_events = [e for e in self._events if e.event_type == "dmip_checkpoint"]
        stand_down_count = 0
        avoid_pair_counts: Dict[str, int] = {}

        for e in dmip_events:
            p = e.payload or {}
            if bool(p.get("stand_down")):
                stand_down_count += 1

            pair_bias = dict(p.get("pair_bias") or {})
            for pair, bias in pair_bias.items():
                if str(bias).upper() == "AVOID":
                    k = str(pair or "").upper()
                    avoid_pair_counts[k] = avoid_pair_counts.get(k, 0) + 1

        if stand_down_count >= 2:
            signals.append(
                {
                    "kind": "trading_dmip_stand_down_cluster",
                    "severity": "medium",
                    "count": stand_down_count,
                    "message": f"Frequent DMIP stand-down decisions detected ({stand_down_count}x).",
                }
            )

        for pair, count in sorted(avoid_pair_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            if count >= 2:
                signals.append(
                    {
                        "kind": "trading_pair_uncertainty_cluster",
                        "severity": "medium",
                        "pair": pair,
                        "count": count,
                        "message": f"Pair repeatedly marked AVOID in DMIP: {pair} ({count}x).",
                    }
                )

        return signals

    def build_summary(self) -> Dict[str, Any]:
        events = self._events
        by_type: Dict[str, int] = {}
        ok_count = 0
        fail_count = 0

        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            if e.ok:
                ok_count += 1
            else:
                fail_count += 1

        weakness = self.build_weakness_signals()

        return {
            "schema_version": "aion.trading_learning_summary.v1",
            "total_events": len(events),
            "ok_count": ok_count,
            "fail_count": fail_count,
            "by_type": by_type,
            "weakness_signal_count": len(weakness),
        }


_GLOBAL_TRADING_LEARNING_CAPTURE: Optional[TradingLearningCaptureRuntime] = None


def get_trading_learning_capture_runtime() -> TradingLearningCaptureRuntime:
    global _GLOBAL_TRADING_LEARNING_CAPTURE
    if _GLOBAL_TRADING_LEARNING_CAPTURE is None:
        _GLOBAL_TRADING_LEARNING_CAPTURE = TradingLearningCaptureRuntime()
    return _GLOBAL_TRADING_LEARNING_CAPTURE