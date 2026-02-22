#!/usr/bin/env python3
from __future__ import annotations

from backend.modules.aion_skills.registry import get_global_skill_registry
from backend.modules.aion_skills.contracts import SkillRunRequest
from backend.modules.aion_skills.execution_adapter import SkillExecutionAdapter
from backend.modules.aion_trading.skill_pack import register_aion_trading_skills


def main() -> None:
    registry = get_global_skill_registry()
    register_aion_trading_skills(registry)
    adapter = SkillExecutionAdapter()

    # 1) Curriculum
    r1 = adapter.run(
        SkillRunRequest(
            skill_id="skill.trading_get_curriculum",
            inputs={},
            session_id="s_trading_smoke",
            turn_id="t1",
        ).validate()
    )

    # 2) Strategy list
    r2 = adapter.run(
        SkillRunRequest(
            skill_id="skill.trading_list_strategies",
            inputs={},
            session_id="s_trading_smoke",
            turn_id="t2",
        ).validate()
    )

    # 3) DMIP checkpoint (with forced LLM disagreement on EUR/USD -> AVOID)
    r3 = adapter.run(
        SkillRunRequest(
            skill_id="skill.trading_run_dmip_checkpoint",
            inputs={
                "checkpoint": "pre_market",
                "market_snapshot": {"pairs": ["EUR/USD", "GBP/USD"], "risk_environment": "mixed"},
                "llm_consultation": {
                    "pairs": {
                        "EUR/USD": {"claude_bias": "bullish", "gpt4_bias": "bearish", "confidence": "high"},
                        "GBP/USD": {"claude_bias": "bullish", "gpt4_bias": "bullish", "confidence": "medium"},
                    }
                },
            },
            session_id="s_trading_smoke",
            turn_id="t3",
        ).validate()
    )

    # 4) Risk validation (valid paper proposal)
    r4 = adapter.run(
        SkillRunRequest(
            skill_id="skill.trading_validate_risk",
            inputs={
                "pair": "EUR/USD",
                "strategy_tier": "tier3_smc_intraday",
                "direction": "BUY",
                "account_mode": "paper",
                "entry": 1.1000,
                "stop_loss": 1.0980,
                "take_profit": 1.1040,
                "account_equity": 10000,
                "risk_pct": 1.0,
                "pip_value": 10.0,
                "stop_pips": 20.0,
                "session_stats": {"losing_trades": 0},
                "account_stats": {"day_risk_used_pct": 0.0, "week_risk_used_pct": 1.0, "drawdown_pct": 0.0},
            },
            session_id="s_trading_smoke",
            turn_id="t4",
        ).validate()
    )

    # 5) Risk validation (should fail: live + over-risk)
    r5 = adapter.run(
        SkillRunRequest(
            skill_id="skill.trading_validate_risk",
            inputs={
                "pair": "EUR/USD",
                "strategy_tier": "tier3_smc_intraday",
                "direction": "BUY",
                "account_mode": "live",
                "entry": 1.1000,
                "stop_loss": 1.0990,
                "take_profit": 1.1010,  # RR too low
                "account_equity": 10000,
                "risk_pct": 5.0,  # violates policy
                "pip_value": 10.0,
                "stop_pips": 10.0,
                "session_stats": {"losing_trades": 3},
                "account_stats": {"day_risk_used_pct": 2.5, "week_risk_used_pct": 5.5, "drawdown_pct": 10.1},
            },
            session_id="s_trading_smoke",
            turn_id="t5",
        ).validate()
    )

    print("runs_ok:", [r1.ok, r2.ok, r3.ok, r4.ok, r5.ok])

    # inspect core outputs
    print("curriculum_ok:", r1.ok, "modules:", len((r1.output or {}).get("modules", [])))
    print("strategy_count:", len((r2.output or {}).get("strategies", [])))

    bsheet = ((r3.output or {}).get("bias_sheet") or {})
    eur = None
    for pb in (bsheet.get("pair_biases") or []):
        if pb.get("pair") == "EUR/USD":
            eur = pb
            break
    print("dmip_checkpoint:", (r3.output or {}).get("checkpoint"))
    print("eurusd_bias_from_disagreement:", (eur or {}).get("bias"))

    print("risk_valid_ok:", (r4.output or {}).get("ok"))
    print("risk_valid_violations:", (((r4.output or {}).get("result") or {}).get("violations") or []))

    print("risk_invalid_ok:", (r5.output or {}).get("ok"))
    print("risk_invalid_violations:", (((r5.output or {}).get("result") or {}).get("violations") or []))

    smoke_ok = all([
        bool(r1.ok),
        bool(r2.ok),
        bool(r3.ok),
        bool(r4.ok),
        bool(r5.ok),  # adapter ok; business result can be false
        ((eur or {}).get("bias") == "AVOID"),
        bool((r4.output or {}).get("ok")) is True,
        bool((r5.output or {}).get("ok")) is False,
    ])
    print("aion_trading_sprint1_smoke_ok:", smoke_ok)


if __name__ == "__main__":
    main()