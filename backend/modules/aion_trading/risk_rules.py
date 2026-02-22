from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.aion_trading.contracts import (
    TradeProposal,
    TradingRiskPolicy,
    RiskValidationResult,
)


DEFAULT_TRADING_RISK_POLICY = TradingRiskPolicy().validate()


def calculate_position_size(
    *,
    account_equity: float,
    risk_pct: float,
    stop_pips: float,
    pip_value: float,
) -> float:
    """
    Position size = (equity * risk%) / (stop_pips * pip_value)
    """
    if account_equity <= 0 or risk_pct <= 0 or stop_pips <= 0 or pip_value <= 0:
        raise ValueError("account_equity, risk_pct, stop_pips, pip_value must be > 0")
    risk_amount = float(account_equity) * (float(risk_pct) / 100.0)
    size = risk_amount / (float(stop_pips) * float(pip_value))
    return float(size)


def _rr_ratio(entry: float, stop_loss: float, take_profit: float, direction: str) -> float:
    d = str(direction or "").upper().strip()
    if d == "BUY":
        risk = float(entry) - float(stop_loss)
        reward = float(take_profit) - float(entry)
    elif d == "SELL":
        risk = float(stop_loss) - float(entry)
        reward = float(entry) - float(take_profit)
    else:
        return 0.0

    if risk <= 0:
        return 0.0
    return float(reward / risk)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def validate_trade_proposal(
    proposal: TradeProposal,
    *,
    policy: Optional[TradingRiskPolicy] = None,
    session_stats: Optional[Dict[str, Any]] = None,
    account_stats: Optional[Dict[str, Any]] = None,
) -> RiskValidationResult:
    """
    Enforces hard invariants. This is the non-negotiable gate.

    Phase 2 scope (paper-first):
    - paper-only auth boundary
    - stop required at entry
    - risk-per-trade max
    - RR min/preferred
    - session loss cap
    - daily/weekly risk caps
    - max drawdown stop
    """
    p = proposal.validate()
    pol = (policy or DEFAULT_TRADING_RISK_POLICY).validate()
    session_stats = dict(session_stats or {})
    account_stats = dict(account_stats or {})

    violations = []
    warnings = []
    derived: Dict[str, Any] = {}

    # Paper-only gate for initial phase
    if bool(pol.paper_only) and str(getattr(p, "account_mode", "")).lower() == "live":
        violations.append("live_trading_blocked_phase_policy")

    # Scope lock (Phase 2: EUR/USD only + London only, if fields exist in proposal)
    pair = str(getattr(p, "pair", "") or "").upper().replace("-", "/")
    session_name = str(getattr(p, "session", "") or "").lower().strip()
    if pair and pair != "EUR/USD":
        violations.append("phase2_pair_scope_locked_eurusd_only")
    if session_name and session_name != "london":
        violations.append("phase2_session_scope_locked_london_only")

    # Required stop loss
    if bool(pol.require_stop_loss_at_entry) and getattr(p, "stop_loss", None) is None:
        violations.append("stop_loss_required_at_entry")

    # Basic price sanity (if fields present)
    entry = getattr(p, "entry", None)
    stop_loss = getattr(p, "stop_loss", None)
    take_profit = getattr(p, "take_profit", None)
    direction = str(getattr(p, "direction", "") or "").upper().strip()

    if entry is None:
        violations.append("entry_required")
    if take_profit is None:
        violations.append("take_profit_required")
    if direction not in {"BUY", "SELL"}:
        violations.append("direction_invalid")

    if entry is not None and stop_loss is not None and direction in {"BUY", "SELL"}:
        try:
            e = float(entry)
            s = float(stop_loss)
            if direction == "BUY" and not (s < e):
                violations.append("stop_loss_not_below_entry_for_buy")
            if direction == "SELL" and not (s > e):
                violations.append("stop_loss_not_above_entry_for_sell")
        except Exception:
            violations.append("invalid_entry_or_stop_loss")

    if entry is not None and take_profit is not None and direction in {"BUY", "SELL"}:
        try:
            e = float(entry)
            tp = float(take_profit)
            if direction == "BUY" and not (tp > e):
                violations.append("take_profit_not_above_entry_for_buy")
            if direction == "SELL" and not (tp < e):
                violations.append("take_profit_not_below_entry_for_sell")
        except Exception:
            violations.append("invalid_entry_or_take_profit")

    # Position size derivation
    try:
        computed_size = calculate_position_size(
            account_equity=float(getattr(p, "account_equity")),
            risk_pct=float(getattr(p, "risk_pct")),
            stop_pips=float(getattr(p, "stop_pips")),
            pip_value=float(getattr(p, "pip_value")),
        )
        derived["computed_size"] = computed_size
    except Exception as e:
        violations.append(f"position_size_calculation_failed:{e}")
        computed_size = None

    # Risk per trade
    risk_pct = _safe_float(getattr(p, "risk_pct", 0.0), 0.0)
    if risk_pct > float(pol.max_risk_per_trade_pct):
        violations.append("risk_per_trade_exceeds_policy")

    # RR check (only if core fields usable)
    try:
        rr = _rr_ratio(
            entry=float(getattr(p, "entry")),
            stop_loss=float(getattr(p, "stop_loss")),
            take_profit=float(getattr(p, "take_profit")),
            direction=str(getattr(p, "direction")),
        )
    except Exception:
        rr = 0.0
    derived["rr_ratio"] = rr

    if rr < float(pol.min_rr):
        violations.append("rr_below_min_policy")
    elif rr < float(pol.preferred_rr):
        warnings.append("rr_below_preferred")

    # Session loss cap (if stats supplied)
    losing_trades = _safe_int(session_stats.get("losing_trades", 0), 0)
    if losing_trades >= int(pol.max_losing_trades_per_session):
        violations.append("session_max_losing_trades_reached")

    # Optional session trade count cap if policy supports it
    max_trades_per_session = getattr(pol, "max_trades_per_session", None)
    if max_trades_per_session is not None:
        session_trade_count = _safe_int(session_stats.get("trade_count", 0), 0)
        if session_trade_count >= int(max_trades_per_session):
            violations.append("session_max_trades_reached")

    # Daily / weekly risk used (if stats supplied)
    day_risk_used_pct = _safe_float(account_stats.get("day_risk_used_pct", 0.0), 0.0)
    week_risk_used_pct = _safe_float(account_stats.get("week_risk_used_pct", 0.0), 0.0)
    drawdown_pct = _safe_float(account_stats.get("drawdown_pct", 0.0), 0.0)

    projected_day = day_risk_used_pct + float(risk_pct)
    projected_week = week_risk_used_pct + float(risk_pct)
    derived["projected_day_risk_used_pct"] = projected_day
    derived["projected_week_risk_used_pct"] = projected_week
    derived["drawdown_pct"] = drawdown_pct

    if projected_day > float(pol.max_risk_per_day_pct):
        violations.append("max_daily_risk_exceeded")
    if projected_week > float(pol.max_risk_per_week_pct):
        violations.append("max_weekly_risk_exceeded")
    if drawdown_pct >= float(pol.max_drawdown_stop_pct):
        violations.append("max_drawdown_stop_triggered")

    # Optional red-event / no-trade window flags passed via session/account stats
    if bool(session_stats.get("red_event_lock", False)):
        violations.append("red_event_stand_down_active")
    if bool(session_stats.get("no_trade_window_active", False)):
        violations.append("no_trade_window_active")
    if bool(account_stats.get("manual_kill_switch", False)):
        violations.append("manual_kill_switch_active")

    derived["policy_snapshot"] = {
        "paper_only": bool(getattr(pol, "paper_only", True)),
        "max_risk_per_trade_pct": float(getattr(pol, "max_risk_per_trade_pct", 0.0)),
        "max_risk_per_day_pct": float(getattr(pol, "max_risk_per_day_pct", 0.0)),
        "max_risk_per_week_pct": float(getattr(pol, "max_risk_per_week_pct", 0.0)),
        "min_rr": float(getattr(pol, "min_rr", 0.0)),
        "preferred_rr": float(getattr(pol, "preferred_rr", 0.0)),
        "max_losing_trades_per_session": int(getattr(pol, "max_losing_trades_per_session", 0)),
        "max_drawdown_stop_pct": float(getattr(pol, "max_drawdown_stop_pct", 0.0)),
    }

    return RiskValidationResult(
        ok=(len(violations) == 0),
        violations=violations,
        warnings=warnings,
        derived=derived,
    ).validate()