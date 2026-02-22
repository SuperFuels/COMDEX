from __future__ import annotations

from typing import Dict, List, Optional

from backend.modules.aion_trading.contracts import StrategySpec


def _specs() -> List[StrategySpec]:
    return [
        StrategySpec(
            strategy_tier="tier1_orderflow_sniping",
            name="Order Flow Sniping (HFT-adjacent)",
            timeframe="sub-minute to 1m",
            allowed_pairs=["EUR/USD", "GBP/USD", "USD/JPY"],
            hold_time_hint="seconds to 5 minutes",
            required_confluence=[
                "orderbook_imbalance",
                "structural_level",
                "liquidity_pool_context",
            ],
            execution_rules=[
                "entry only when order flow aligns with structural level",
                "max hold 5 minutes",
                "no trade first 2 minutes of session open",
                "wait for hft footprint exhaustion before entry",
            ],
            risk_notes=[
                "paper-only until verified",
                "microstructure false signals common",
            ],
        ),
        StrategySpec(
            strategy_tier="tier2_momentum_orb",
            name="Momentum / Opening Range Breakout",
            timeframe="1m to 15m",
            allowed_pairs=["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"],
            hold_time_hint="minutes to hours",
            required_confluence=[
                "opening_range",
                "volume_confirmation",
                "higher_timeframe_alignment",
            ],
            execution_rules=[
                "prefer retest entries over breakout chase",
                "avoid red-event windows",
                "stop beyond invalidation level",
            ],
            risk_notes=["whipsaw risk around opens and data releases"],
        ),
        StrategySpec(
            strategy_tier="tier3_smc_intraday",
            name="SMC Intraday (Liquidity Grab + Return)",
            timeframe="15m to 1h",
            allowed_pairs=["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF"],
            hold_time_hint="hours",
            required_confluence=[
                "liquidity_sweep",
                "choch_or_bos",
                "order_block_or_fvg_reentry",
                "session_context",
            ],
            execution_rules=[
                "wait for sweep confirmation and structure shift",
                "enter on retrace into OB/FVG",
                "target opposite liquidity pool / imbalance",
            ],
            risk_notes=["best first implementation strategy for AION paper training"],
        ),
        StrategySpec(
            strategy_tier="tier4_swing",
            name="Swing Trading",
            timeframe="4h to daily",
            allowed_pairs=["all_majors"],
            hold_time_hint="2 to 10 days",
            required_confluence=[
                "higher_timeframe_structure_break",
                "fundamental_alignment",
                "weekly_monthly_level",
            ],
            execution_rules=[
                "entry on first pullback after break",
                "trail after 1:1",
                "respect event exposure",
            ],
            risk_notes=["longer feedback loops; slower learning"],
        ),
        StrategySpec(
            strategy_tier="tier5_macro_positioning",
            name="Macro Positioning",
            timeframe="weekly",
            allowed_pairs=["macro-selected majors"],
            hold_time_hint="weeks to months",
            required_confluence=[
                "central_bank_divergence",
                "macro_theme",
                "capital_flow_direction",
            ],
            execution_rules=[
                "used as directional filter for lower strategies",
                "weekly review and bias update",
            ],
            risk_notes=["not first execution strategy; context layer first"],
        ),
    ]


def get_strategy_registry() -> Dict[str, StrategySpec]:
    out: Dict[str, StrategySpec] = {}
    for spec in _specs():
        out[spec.strategy_tier] = spec.validate()
    return out


def get_strategy_spec(strategy_tier: str) -> Optional[StrategySpec]:
    return get_strategy_registry().get(str(strategy_tier or "").strip())


def list_strategy_specs() -> List[dict]:
    return [s.to_dict() for s in get_strategy_registry().values()]