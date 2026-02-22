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
    if direction == "BUY":
        risk = entry - stop_loss
        reward = take_profit - entry
    else:
        risk = stop_loss - entry
        reward = entry - take_profit
    if risk <= 0:
        return 0.0
    return float(reward / risk)


def validate_trade_proposal(
    proposal: TradeProposal,
    *,
    policy: Optional[TradingRiskPolicy] = None,
    session_stats: Optional[Dict[str, Any]] = None,
    account_stats: Optional[Dict[str, Any]] = None,
) -> RiskValidationResult:
    """
    Enforces hard invariants. This is the non-negotiable gate.
    """
    p = proposal.validate()
    pol = (policy or DEFAULT_TRADING_RISK_POLICY).validate()
    session_stats = dict(session_stats or {})
    account_stats = dict(account_stats or {})

    violations = []
    warnings = []
    derived: Dict[str, Any] = {}

    # Paper-only gate for initial phase
    if pol.paper_only and p.account_mode == "live":
        violations.append("live_trading_blocked_phase_policy")

    # Required stop loss
    if pol.require_stop_loss_at_entry and p.stop_loss is None:
        violations.append("stop_loss_required_at_entry")

    # Position size derivation
    try:
        computed_size = calculate_position_size(
            account_equity=p.account_equity,
            risk_pct=p.risk_pct,
            stop_pips=p.stop_pips,
            pip_value=p.pip_value,
        )
        derived["computed_size"] = computed_size
    except Exception as e:
        violations.append(f"position_size_calculation_failed:{e}")
        computed_size = None

    # Risk per trade
    if p.risk_pct > pol.max_risk_per_trade_pct:
        violations.append("risk_per_trade_exceeds_policy")

    # RR check
    rr = _rr_ratio(
        entry=float(p.entry),
        stop_loss=float(p.stop_loss),
        take_profit=float(p.take_profit),
        direction=p.direction,
    )
    derived["rr_ratio"] = rr
    if rr < float(pol.min_rr):
        violations.append("rr_below_min_policy")
    elif rr < float(pol.preferred_rr):
        warnings.append("rr_below_preferred")

    # Session loss cap (if stats supplied)
    losing_trades = int(session_stats.get("losing_trades", 0) or 0)
    if losing_trades >= int(pol.max_losing_trades_per_session):
        violations.append("session_max_losing_trades_reached")

    # Daily / weekly risk used (if stats supplied)
    day_risk_used_pct = float(account_stats.get("day_risk_used_pct", 0.0) or 0.0)
    week_risk_used_pct = float(account_stats.get("week_risk_used_pct", 0.0) or 0.0)
    drawdown_pct = float(account_stats.get("drawdown_pct", 0.0) or 0.0)

    projected_day = day_risk_used_pct + float(p.risk_pct)
    projected_week = week_risk_used_pct + float(p.risk_pct)
    derived["projected_day_risk_used_pct"] = projected_day
    derived["projected_week_risk_used_pct"] = projected_week
    derived["drawdown_pct"] = drawdown_pct

    if projected_day > pol.max_risk_per_day_pct:
        violations.append("max_daily_risk_exceeded")
    if projected_week > pol.max_risk_per_week_pct:
        violations.append("max_weekly_risk_exceeded")
    if drawdown_pct >= pol.max_drawdown_stop_pct:
        violations.append("max_drawdown_stop_triggered")

    return RiskValidationResult(
        ok=(len(violations) == 0),
        violations=violations,
        warnings=warnings,
        derived=derived,
    ).validate()