from __future__ import annotations

from backend.modules.aion_trading.learning_capture import get_trading_learning_capture_runtime


def setup_function():
    rt = get_trading_learning_capture_runtime()
    rt.clear()


def test_log_risk_validation_event_and_summary():
    rt = get_trading_learning_capture_runtime()

    ev = rt.log_risk_validation_event(
        session_id="s1",
        turn_id="t1",
        skill_id="skill.trading_validate_risk",
        skill_output={
            "ok": False,
            "result": {
                "violations": ["rr_below_min_policy", "risk_per_trade_exceeds_policy"],
                "risk_reward_ratio": 1.2,
            },
            "proposal": {
                "pair": "EUR/USD",
                "strategy_tier": "tier3_smc_intraday",
                "direction": "BUY",
                "account_mode": "paper",
                "risk_pct": 2.0,
                "stop_pips": 50,
            },
        },
    )

    assert ev["event_type"] == "risk_validation"
    assert ev["ok"] is False

    summary = rt.build_summary()
    assert summary["total_events"] == 1
    assert summary["by_type"]["risk_validation"] == 1
    assert summary["fail_count"] == 1


def test_weakness_signals_for_repeated_low_rr_and_violations():
    rt = get_trading_learning_capture_runtime()

    for i in range(3):
        rt.log_risk_validation_event(
            session_id="s1",
            turn_id=f"t{i}",
            skill_id="skill.trading_validate_risk",
            skill_output={
                "ok": False,
                "result": {
                    "violations": ["rr_below_min_policy", "max_daily_risk_exceeded"],
                    "risk_reward_ratio": 1.5,
                },
                "proposal": {
                    "pair": "EUR/USD",
                    "strategy_tier": "tier3_smc_intraday",
                    "direction": "BUY",
                    "account_mode": "paper",
                    "risk_pct": 1.5,
                    "stop_pips": 40,
                },
            },
        )

    signals = rt.build_weakness_signals()
    kinds = {s.get("kind") for s in signals}

    assert "trading_risk_violation_frequency" in kinds
    assert "trading_low_rr_proposals" in kinds
    assert "trading_repeated_invalid_proposals" in kinds


def test_dmip_avoid_pair_cluster_signal():
    rt = get_trading_learning_capture_runtime()

    for i in range(2):
        rt.log_dmip_checkpoint_event(
            session_id="s2",
            turn_id=f"d{i}",
            skill_id="skill.trading_run_dmip_checkpoint",
            skill_output={
                "ok": True,
                "checkpoint": "pre_market",
                "bias_sheet": {
                    "pair_bias": {
                        "EUR/USD": "AVOID",
                        "GBP/USD": "BULLISH",
                    },
                    "trading_confidence": "LOW",
                    "risk_environment": "MIXED",
                },
            },
        )

    signals = rt.build_weakness_signals()
    pair_signals = [s for s in signals if s.get("kind") == "trading_pair_uncertainty_cluster"]
    assert len(pair_signals) >= 1
    assert any(s.get("pair") == "EUR/USD" for s in pair_signals)