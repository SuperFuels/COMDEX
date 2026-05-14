# /workspaces/COMDEX/backend/tests/test_aion_trading_decision_event_schema.py
from __future__ import annotations

from backend.modules.aion_trading.trading_decision_event_schema import (
    build_trading_decision_event,
    validate_trading_decision_event,
)


def test_decision_event_requires_process_and_snapshot_hash():
    event = build_trading_decision_event(
        session_id="s1",
        event_type="dmip_bias",
        instrument="EUR/USD",
        timeframe="M15",
        side_bias="bullish",
        decision={"action": "watch_long"},
        decision_influence_snapshot_hash="abc123" * 10 + "abcd",  # 64-ish string not strictly enforced
        process_score={
            "quality": 0.78,
            "confidence": 0.66,
            "checklist_pass_rate": 0.9,
            "violations": [],
        },
        outcome_score={
            "status": "pending",
            "pnl_r": None,
            "mae_r": None,
            "mfe_r": None,
            "bias_correct": None,
            "scored_at": None,
        },
    )

    vr = validate_trading_decision_event(event)
    assert vr.ok is True


def test_decision_event_rejects_missing_process_score_fields():
    event = build_trading_decision_event(
        session_id="s2",
        event_type="risk_validation",
        instrument="GBP/USD",
        timeframe=None,
        side_bias=None,
        decision={"approved": True},
        decision_influence_snapshot_hash="f" * 64,
        process_score={"quality": 0.4},  # missing confidence
    )
    vr = validate_trading_decision_event(event)
    assert vr.ok is False
    assert any("missing_process_score_field:confidence" == e for e in vr.errors)