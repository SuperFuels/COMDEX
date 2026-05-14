from __future__ import annotations

from typing import Any, Dict, List

from backend.modules.aion_trading.strategy_registry import list_strategy_specs
from backend.modules.aion_trading.contracts import TradingRiskPolicy


FOREX_KNOWLEDGE_CURRICULUM_V1: List[Dict[str, Any]] = [
    {
        "module_id": "market_structure_basics",
        "title": "Forex Market Structure & Mechanics",
        "priority": 1,
        "must_master_before": ["live_execution", "paper_execution"],
        "topics": [
            "base_quote_bid_ask_spread",
            "sessions_liquidity_windows",
            "participants_market_makers_lp_hft_retail",
            "price_discovery_otc_market",
        ],
    },
    {
        "module_id": "risk_management_invariants",
        "title": "Risk Management Rules (Absolute Invariants)",
        "priority": 1,
        "must_master_before": ["paper_execution", "strategy_progression"],
        "topics": [
            "risk_per_trade_day_week_caps",
            "stop_loss_required_at_entry",
            "rr_minimum_and_preferred",
            "max_losing_trades_per_session",
            "drawdown_hard_stop",
        ],
    },
    {
        "module_id": "price_action_and_smc",
        "title": "Price Action + SMC Foundations",
        "priority": 2,
        "must_master_before": ["tier3_smc_intraday_execution"],
        "topics": [
            "candlestick_structure",
            "support_resistance",
            "bos_choch",
            "order_blocks",
            "fair_value_gaps",
            "liquidity_sweeps",
        ],
    },
    {
        "module_id": "order_flow_microstructure",
        "title": "Order Flow & Market Microstructure",
        "priority": 3,
        "must_master_before": ["tier1_orderflow_sniping_execution"],
        "topics": [
            "l2_orderbook_depth",
            "footprint_delta",
            "iceberg_absorption",
            "stop_hunt_signatures",
            "liquidity_pool_mapping",
        ],
    },
    {
        "module_id": "dmip_market_intelligence",
        "title": "Daily Market Intelligence Protocol",
        "priority": 2,
        "must_master_before": ["session_trading"],
        "topics": [
            "morning_briefing_bias_sheet",
            "session_checkpoints",
            "red_amber_event_protocol",
            "stand_down_conditions",
            "multi_llm_verification_logic",
        ],
    },
    {
        "module_id": "process_vs_outcome_learning",
        "title": "Trading Learning Loop (Process vs Outcome)",
        "priority": 2,
        "must_master_before": ["strategy_weight_adjustment"],
        "topics": [
            "good_process_bad_outcome",
            "bad_process_good_outcome",
            "reward_signal_design",
            "pattern_clustering",
            "session_debrief_review",
        ],
    },
]


def get_forex_curriculum_v1() -> Dict[str, Any]:
    return {
        "schema_version": "aion.forex_curriculum.v1",
        "summary": {
            "phase": "phase_t_sprint1",
            "goal": "teach_aion_how_trading_works_before_execution",
            "paper_only": True,
            "starting_pair": "EUR/USD",
            "starting_strategy": "tier3_smc_intraday",
        },
        "risk_policy": TradingRiskPolicy().validate().to_dict(),
        "strategy_specs": list_strategy_specs(),
        "modules": list(FOREX_KNOWLEDGE_CURRICULUM_V1),
    }