# /workspaces/COMDEX/backend/tests/test_aion_trading_dmip_learning_summary.py
from __future__ import annotations

import importlib
import time
from typing import Any, Dict, List, Tuple

import pytest

# Use importlib (safer in your repo layout during test collection)
summ = importlib.import_module("backend.modules.aion_trading.dmip_learning_summary")


def _mk_llm_row(
    *,
    ts: float,
    pair: str,
    checkpoint: str,
    agreement: str,
    selected_bias: str,
    confidence: str,
    claude_bias: str = "",
    gpt4_bias: str = "",
) -> Dict[str, Any]:
    return {
        "schema_version": "aion.dmip_llm_accuracy_event.v1",
        "event_id": f"evt_{int(ts)}_{pair.replace('/', '')}",
        "timestamp_unix": ts,
        "checkpoint": checkpoint,
        "pair": pair,
        "source": "dmip_runtime",
        "agreement": agreement,
        "selected_bias": selected_bias,
        "confidence": confidence,
        "llm_pair": {
            "claude_bias": claude_bias or selected_bias,
            "gpt4_bias": gpt4_bias or selected_bias,
            "confidence": confidence,
            "key_levels": [],
            "has_extra_fields": False,
        },
        "metadata": {
            "capture_layer": "dmip_learning_capture",
            "non_blocking": True,
            "paper_safe": True,
        },
    }


def test_summarize_llm_accuracy_with_synthetic_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    now = time.time()
    rows = [
        _mk_llm_row(
            ts=now - 60,
            pair="EUR/USD",
            checkpoint="london",
            agreement="agree",
            selected_bias="BULLISH",
            confidence="MEDIUM",
            claude_bias="BULLISH",
            gpt4_bias="BULLISH",
        ),
        _mk_llm_row(
            ts=now - 50,
            pair="EUR/USD",
            checkpoint="london",
            agreement="disagree",
            selected_bias="AVOID",
            confidence="LOW",
            claude_bias="BULLISH",
            gpt4_bias="BEARISH",
        ),
        _mk_llm_row(
            ts=now - 40,
            pair="GBP/USD",
            checkpoint="new_york",
            agreement="agree",
            selected_bias="BEARISH",
            confidence="HIGH",
            claude_bias="BEARISH",
            gpt4_bias="BEARISH",
        ),
        _mk_llm_row(
            ts=now - 30,
            pair="USD/JPY",
            checkpoint="london",
            agreement="partial",
            selected_bias="NEUTRAL",
            confidence="LOW",
            claude_bias="NEUTRAL",
            gpt4_bias="",
        ),
    ]

    def _fake_read_jsonl_rows(*args: Any, **kwargs: Any) -> Tuple[List[Dict[str, Any]], None]:
        return rows, None

    monkeypatch.setattr(summ, "_read_jsonl_rows", _fake_read_jsonl_rows)

    out = summ.summarize_llm_accuracy(days=30)

    assert out["ok"] is True
    assert int(((out.get("totals") or {}).get("sample_size") or 0)) == 4

    by_pair = out.get("by_pair") or {}
    assert "EUR/USD" in by_pair
    assert int(((by_pair["EUR/USD"]).get("sample_size") or 0)) == 2

    agreement_counts = ((out.get("totals") or {}).get("agreement_counts") or {})
    assert "agree" in agreement_counts
    assert "disagree" in agreement_counts
    assert int(agreement_counts.get("agree", 0)) >= 1
    assert int(agreement_counts.get("disagree", 0)) >= 1


def test_get_llm_weighting_summary_focus_bucket_and_hints(monkeypatch: pytest.MonkeyPatch) -> None:
    now = time.time()
    rows = [
        _mk_llm_row(
            ts=now - 100,
            pair="EUR/USD",
            checkpoint="london",
            agreement="agree",
            selected_bias="BULLISH",
            confidence="MEDIUM",
            claude_bias="BULLISH",
            gpt4_bias="BULLISH",
        ),
        _mk_llm_row(
            ts=now - 90,
            pair="EUR/USD",
            checkpoint="london",
            agreement="agree",
            selected_bias="BULLISH",
            confidence="HIGH",
            claude_bias="BULLISH",
            gpt4_bias="BULLISH",
        ),
        _mk_llm_row(
            ts=now - 80,
            pair="EUR/USD",
            checkpoint="new_york",
            agreement="disagree",
            selected_bias="AVOID",
            confidence="LOW",
            claude_bias="BULLISH",
            gpt4_bias="BEARISH",
        ),
    ]

    def _fake_read_jsonl_rows(*args: Any, **kwargs: Any) -> Tuple[List[Dict[str, Any]], None]:
        return rows, None

    monkeypatch.setattr(summ, "_read_jsonl_rows", _fake_read_jsonl_rows)

    out = summ.get_llm_weighting_summary(days=30, pair="EUR/USD", checkpoint="london")

    assert out["ok"] is True
    focus = out.get("focus") or {}
    bucket = focus.get("bucket") or {}
    assert int(bucket.get("sample_size", 0)) >= 1

    hints = out.get("weighting_hints") or {}
    assert hints.get("confidence_band") in {"LOW", "MEDIUM", "HIGH"}


def test_summarize_llm_accuracy_read_failure_non_breaking(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_read_jsonl_rows(*args: Any, **kwargs: Any) -> Tuple[List[Dict[str, Any]], str]:
        return [], "jsonl_read_error:boom"

    monkeypatch.setattr(summ, "_read_jsonl_rows", _fake_read_jsonl_rows)

    # should not raise
    out = summ.summarize_llm_accuracy(days=30)

    assert isinstance(out, dict)
    assert out["ok"] is False
    assert out.get("non_blocking") is True
    assert out.get("error") == "llm_accuracy_summary_read_error"


def test_time_window_filter_only_recent_counted_when_days_7(monkeypatch: pytest.MonkeyPatch) -> None:
    now = time.time()
    rows = [
        _mk_llm_row(
            ts=now - (2 * 86400),  # recent (2 days ago)
            pair="EUR/USD",
            checkpoint="london",
            agreement="agree",
            selected_bias="BULLISH",
            confidence="MEDIUM",
        ),
        _mk_llm_row(
            ts=now - (10 * 86400),  # old (10 days ago)
            pair="EUR/USD",
            checkpoint="london",
            agreement="disagree",
            selected_bias="AVOID",
            confidence="LOW",
            claude_bias="BULLISH",
            gpt4_bias="BEARISH",
        ),
    ]

    def _fake_read_jsonl_rows(*args: Any, **kwargs: Any) -> Tuple[List[Dict[str, Any]], None]:
        return rows, None

    monkeypatch.setattr(summ, "_read_jsonl_rows", _fake_read_jsonl_rows)

    out = summ.summarize_llm_accuracy(days=7)

    totals = out.get("totals") or {}
    assert out["ok"] is True
    assert int(totals.get("sample_size", 0)) == 1

    agreement_counts = totals.get("agreement_counts") or {}
    assert int(agreement_counts.get("agree", 0)) == 1
    assert int(agreement_counts.get("disagree", 0)) == 0