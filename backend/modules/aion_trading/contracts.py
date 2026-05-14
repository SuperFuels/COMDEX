from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ALLOWED_STRATEGY_TIERS = {
    "tier1_orderflow_sniping",
    "tier2_momentum_orb",
    "tier3_smc_intraday",
    "tier4_swing",
    "tier5_macro_positioning",
}

ALLOWED_BIAS = {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"}
ALLOWED_CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
ALLOWED_RISK_ENV = {"RISK_ON", "RISK_OFF", "MIXED", "UNKNOWN"}
ALLOWED_SESSION = {"pre_market", "london", "mid_london", "new_york", "asia", "eod"}
ALLOWED_ACCOUNT_MODE = {"paper", "sim", "live"}  # live exists in schema, but runtime can block it


@dataclass
class TradingRiskPolicy:
    schema_version: str = "aion.trading_risk_policy.v1"

    max_risk_per_trade_pct: float = 1.0
    max_risk_per_day_pct: float = 3.0
    max_risk_per_week_pct: float = 6.0
    max_drawdown_stop_pct: float = 10.0

    min_rr: float = 2.0
    preferred_rr: float = 3.0

    max_losing_trades_per_session: int = 3
    require_stop_loss_at_entry: bool = True
    forbid_averaging_down: bool = True
    forbid_stop_widening: bool = True

    paper_only: bool = True

    def validate(self) -> "TradingRiskPolicy":
        if self.schema_version != "aion.trading_risk_policy.v1":
            raise ValueError("schema_version must be aion.trading_risk_policy.v1")
        for name in [
            "max_risk_per_trade_pct",
            "max_risk_per_day_pct",
            "max_risk_per_week_pct",
            "max_drawdown_stop_pct",
            "min_rr",
            "preferred_rr",
        ]:
            if float(getattr(self, name)) <= 0:
                raise ValueError(f"{name} must be > 0")
        if self.max_losing_trades_per_session < 1:
            raise ValueError("max_losing_trades_per_session must be >= 1")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_risk_per_trade_pct": self.max_risk_per_trade_pct,
            "max_risk_per_day_pct": self.max_risk_per_day_pct,
            "max_risk_per_week_pct": self.max_risk_per_week_pct,
            "max_drawdown_stop_pct": self.max_drawdown_stop_pct,
            "min_rr": self.min_rr,
            "preferred_rr": self.preferred_rr,
            "max_losing_trades_per_session": self.max_losing_trades_per_session,
            "require_stop_loss_at_entry": self.require_stop_loss_at_entry,
            "forbid_averaging_down": self.forbid_averaging_down,
            "forbid_stop_widening": self.forbid_stop_widening,
            "paper_only": self.paper_only,
        }


@dataclass
class PairBias:
    pair: str
    bias: str = "NEUTRAL"
    confidence: str = "LOW"
    key_levels: List[float] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def validate(self) -> "PairBias":
        if not str(self.pair).strip():
            raise ValueError("pair is required")
        if self.bias not in ALLOWED_BIAS:
            raise ValueError(f"bias must be one of {sorted(ALLOWED_BIAS)}")
        if self.confidence not in ALLOWED_CONFIDENCE:
            raise ValueError(f"confidence must be one of {sorted(ALLOWED_CONFIDENCE)}")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": self.pair,
            "bias": self.bias,
            "confidence": self.confidence,
            "key_levels": list(self.key_levels or []),
            "notes": list(self.notes or []),
        }


@dataclass
class DailyBiasSheet:
    schema_version: str = "aion.daily_bias_sheet.v1"
    checkpoint_id: str = ""
    session: str = "pre_market"
    risk_environment: str = "UNKNOWN"
    trading_confidence: str = "LOW"
    pair_biases: List[PairBias] = field(default_factory=list)
    avoid_events: List[str] = field(default_factory=list)
    llm_agreement_flags: Dict[str, str] = field(default_factory=dict)  # pair -> agreement/disagreement
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "DailyBiasSheet":
        if self.schema_version != "aion.daily_bias_sheet.v1":
            raise ValueError("schema_version must be aion.daily_bias_sheet.v1")
        if self.session not in ALLOWED_SESSION:
            raise ValueError(f"session must be one of {sorted(ALLOWED_SESSION)}")
        if self.risk_environment not in ALLOWED_RISK_ENV:
            raise ValueError(f"risk_environment must be one of {sorted(ALLOWED_RISK_ENV)}")
        if self.trading_confidence not in ALLOWED_CONFIDENCE:
            raise ValueError(f"trading_confidence must be one of {sorted(ALLOWED_CONFIDENCE)}")
        for pb in self.pair_biases:
            pb.validate()
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "checkpoint_id": self.checkpoint_id,
            "session": self.session,
            "risk_environment": self.risk_environment,
            "trading_confidence": self.trading_confidence,
            "pair_biases": [x.to_dict() for x in self.pair_biases],
            "avoid_events": list(self.avoid_events or []),
            "llm_agreement_flags": dict(self.llm_agreement_flags or {}),
            "metadata": dict(self.metadata or {}),
        }


@dataclass
class TradeProposal:
    schema_version: str = "aion.trade_proposal.v1"
    pair: str = ""
    strategy_tier: str = "tier3_smc_intraday"
    direction: str = "BUY"  # BUY/SELL
    account_mode: str = "paper"

    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    account_equity: float = 0.0
    risk_pct: float = 0.0
    pip_value: float = 0.0
    stop_pips: float = 0.0
    size: Optional[float] = None

    thesis: str = ""
    setup_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "TradeProposal":
        if self.schema_version != "aion.trade_proposal.v1":
            raise ValueError("schema_version must be aion.trade_proposal.v1")
        if not str(self.pair).strip():
            raise ValueError("pair is required")
        if self.strategy_tier not in ALLOWED_STRATEGY_TIERS:
            raise ValueError(f"strategy_tier must be one of {sorted(ALLOWED_STRATEGY_TIERS)}")
        if self.direction not in {"BUY", "SELL"}:
            raise ValueError("direction must be BUY or SELL")
        if self.account_mode not in ALLOWED_ACCOUNT_MODE:
            raise ValueError(f"account_mode must be one of {sorted(ALLOWED_ACCOUNT_MODE)}")
        if self.entry is None or self.stop_loss is None or self.take_profit is None:
            raise ValueError("entry, stop_loss, take_profit are required")
        if self.account_equity <= 0:
            raise ValueError("account_equity must be > 0")
        if self.risk_pct <= 0:
            raise ValueError("risk_pct must be > 0")
        if self.pip_value <= 0:
            raise ValueError("pip_value must be > 0")
        if self.stop_pips <= 0:
            raise ValueError("stop_pips must be > 0")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "pair": self.pair,
            "strategy_tier": self.strategy_tier,
            "direction": self.direction,
            "account_mode": self.account_mode,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "account_equity": self.account_equity,
            "risk_pct": self.risk_pct,
            "pip_value": self.pip_value,
            "stop_pips": self.stop_pips,
            "size": self.size,
            "thesis": self.thesis,
            "setup_tags": list(self.setup_tags or []),
            "metadata": dict(self.metadata or {}),
        }


@dataclass
class RiskValidationResult:
    schema_version: str = "aion.risk_validation_result.v1"
    ok: bool = False
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    derived: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "RiskValidationResult":
        if self.schema_version != "aion.risk_validation_result.v1":
            raise ValueError("schema_version must be aion.risk_validation_result.v1")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ok": bool(self.ok),
            "violations": list(self.violations or []),
            "warnings": list(self.warnings or []),
            "derived": dict(self.derived or {}),
        }


@dataclass
class StrategySpec:
    schema_version: str = "aion.strategy_spec.v1"
    strategy_tier: str = "tier3_smc_intraday"
    name: str = ""
    timeframe: str = ""
    allowed_pairs: List[str] = field(default_factory=list)
    hold_time_hint: str = ""
    required_confluence: List[str] = field(default_factory=list)
    execution_rules: List[str] = field(default_factory=list)
    risk_notes: List[str] = field(default_factory=list)

    def validate(self) -> "StrategySpec":
        if self.schema_version != "aion.strategy_spec.v1":
            raise ValueError("schema_version must be aion.strategy_spec.v1")
        if self.strategy_tier not in ALLOWED_STRATEGY_TIERS:
            raise ValueError(f"strategy_tier must be one of {sorted(ALLOWED_STRATEGY_TIERS)}")
        if not self.name.strip():
            raise ValueError("name is required")
        if not self.timeframe.strip():
            raise ValueError("timeframe is required")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "strategy_tier": self.strategy_tier,
            "name": self.name,
            "timeframe": self.timeframe,
            "allowed_pairs": list(self.allowed_pairs or []),
            "hold_time_hint": self.hold_time_hint,
            "required_confluence": list(self.required_confluence or []),
            "execution_rules": list(self.execution_rules or []),
            "risk_notes": list(self.risk_notes or []),
        }


@dataclass
class TradingDecisionRecord:
    """
    Learning-ready record: process quality is tracked separately from outcome quality.
    """
    schema_version: str = "aion.trading_decision_record.v1"
    decision_id: str = ""
    session_id: str = ""
    pair: str = ""
    strategy_tier: str = ""
    action: str = "NO_TRADE"  # NO_TRADE / PROPOSE_TRADE / EXECUTE_PAPER / CLOSE
    process_quality_score: float = 0.0
    outcome_score: float = 0.0
    reward_score: float = 0.0
    reasoning: Dict[str, Any] = field(default_factory=dict)
    outcome: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "TradingDecisionRecord":
        if self.schema_version != "aion.trading_decision_record.v1":
            raise ValueError("schema_version must be aion.trading_decision_record.v1")
        if not str(self.decision_id).strip():
            raise ValueError("decision_id is required")
        if not str(self.action).strip():
            raise ValueError("action is required")
        for k in ["process_quality_score", "outcome_score", "reward_score"]:
            v = float(getattr(self, k))
            if v < -1.0 or v > 1.0:
                raise ValueError(f"{k} must be between -1.0 and 1.0")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "session_id": self.session_id,
            "pair": self.pair,
            "strategy_tier": self.strategy_tier,
            "action": self.action,
            "process_quality_score": self.process_quality_score,
            "outcome_score": self.outcome_score,
            "reward_score": self.reward_score,
            "reasoning": dict(self.reasoning or {}),
            "outcome": dict(self.outcome or {}),
            "tags": list(self.tags or []),
            "metadata": dict(self.metadata or {}),
        }