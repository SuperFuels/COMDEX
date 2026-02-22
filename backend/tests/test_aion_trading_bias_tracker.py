# /workspaces/COMDEX/backend/tests/test_aion_trading_bias_tracker.py
from __future__ import annotations

from backend.modules.aion_trading.trading_bias_tracker import (
    build_bias_tracker_summary,
    score_bias_correct,
)


def test_score_bias_correct():
    assert score_bias_correct("bullish", "bullish") is True
    assert score_bias_correct("bearish", "bullish") is False
    assert score_bias_correct("neutral", "neutral") is True
    assert score_bias_correct("invalid", "bullish") is None


def test_bias_tracker_summary_accuracy():
    records = [
        {"instrument": "EUR/USD", "bias_correct": True},
        {"instrument": "EUR/USD", "bias_correct": False},
        {"instrument": "GBP/USD", "bias_correct": True},
        {"instrument": "GBP/USD", "bias_correct": None},
    ]
    s = build_bias_tracker_summary(records)
    assert s["total_records"] == 4
    assert s["resolved_records"] == 3
    assert s["correct_records"] == 2
    assert abs(s["accuracy"] - (2/3)) < 1e-6