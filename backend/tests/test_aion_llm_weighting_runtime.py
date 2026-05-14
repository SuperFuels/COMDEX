# /workspaces/COMDEX/backend/tests/test_aion_llm_weighting_runtime.py
from __future__ import annotations

from pathlib import Path

from backend.modules.aion_learning.llm_weighting_runtime import LLMWeightingRuntime


def _mk(tmp_path: Path) -> LLMWeightingRuntime:
    return LLMWeightingRuntime(accuracy_log_path=tmp_path / "llm_accuracy_log.jsonl")


def test_log_llm_accuracy_and_summary_basic(tmp_path):
    rt = _mk(tmp_path)

    rt.log_llm_accuracy(
        llm_id="claude",
        pair="EUR/USD",
        session="london",
        task_type="directional_bias",
        predicted_bias="BULLISH",
        actual_outcome_bias="BULLISH",
        confidence="HIGH",
    )
    rt.log_llm_accuracy(
        llm_id="gpt4",
        pair="EUR/USD",
        session="london",
        task_type="directional_bias",
        predicted_bias="BEARISH",
        actual_outcome_bias="BULLISH",
        confidence="MEDIUM",
    )

    out = rt.summarize_llm_accuracy(pair="EUR/USD", session="london", task_type="directional_bias")

    assert out["ok"] is True
    assert out["matched_rows"] == 2
    assert "claude" in out["per_llm"]
    assert "gpt4" in out["per_llm"]

    claude = out["per_llm"]["claude"]
    gpt4 = out["per_llm"]["gpt4"]

    assert claude["n"] == 1
    assert claude["correct_n"] == 1
    assert claude["incorrect_n"] == 0
    assert float(claude["accuracy"]) == 1.0

    assert gpt4["n"] == 1
    assert gpt4["correct_n"] == 0
    assert gpt4["incorrect_n"] == 1
    assert float(gpt4["accuracy"]) == 0.0


def test_synthesise_agreement_returns_agree_and_non_avoid(tmp_path):
    rt = _mk(tmp_path)

    # seed performance (optional, but useful)
    rt.log_llm_accuracy(
        llm_id="claude",
        pair="EUR/USD",
        session="london",
        predicted_bias="BULLISH",
        actual_outcome_bias="BULLISH",
    )
    rt.log_llm_accuracy(
        llm_id="gpt4",
        pair="EUR/USD",
        session="london",
        predicted_bias="BULLISH",
        actual_outcome_bias="BULLISH",
    )

    out = rt.get_llm_weighted_bias(
        pair="EUR/USD",
        session="london",
        llm_pair={
            "claude_bias": "BULLISH",
            "gpt4_bias": "BULLISH",
            "claude_confidence": "HIGH",
            "gpt4_confidence": "MEDIUM",
        },
    )

    assert out["ok"] is True
    assert out["agreement_flag"] == "agree"
    assert out["avoid"] is False
    assert out["bias"] == "BULLISH"
    assert out["confidence"] in {"MEDIUM", "HIGH"}
    assert "llm_agreement" in out["reasons"]


def test_synthesise_hard_disagreement_forces_avoid(tmp_path):
    rt = _mk(tmp_path)

    out = rt.get_llm_weighted_bias(
        pair="EUR/USD",
        session="london",
        llm_pair={
            "claude_bias": "BULLISH",
            "gpt4_bias": "BEARISH",
            "confidence": "HIGH",
        },
    )

    assert out["ok"] is True
    assert out["agreement_flag"] == "hard_disagree"
    assert out["avoid"] is True
    assert out["bias"] == "AVOID"
    assert out["confidence"] == "LOW"
    assert "llm_disagreement_pair_avoid" in out["reasons"]


def test_synthesise_partial_single_source(tmp_path):
    rt = _mk(tmp_path)

    out = rt.get_llm_weighted_bias(
        pair="EUR/USD",
        session="london",
        llm_pair={
            "claude_bias": "NEUTRAL",
            "claude_confidence": "LOW",
        },
    )

    assert out["ok"] is True
    assert out["agreement_flag"] == "partial"
    assert out["avoid"] is False
    assert out["bias"] == "NEUTRAL"
    assert "single_llm_input_partial" in out["reasons"]


def test_weighting_uses_empirical_accuracy_when_available(tmp_path):
    rt = _mk(tmp_path)

    # claude strong recent record
    for _ in range(8):
        rt.log_llm_accuracy(
            llm_id="claude",
            pair="EUR/USD",
            session="london",
            predicted_bias="BULLISH",
            actual_outcome_bias="BULLISH",
        )
    # gpt4 weak recent record
    for _ in range(8):
        rt.log_llm_accuracy(
            llm_id="gpt4",
            pair="EUR/USD",
            session="london",
            predicted_bias="BEARISH",
            actual_outcome_bias="BULLISH",
        )

    out = rt.get_llm_weighted_bias(
        pair="EUR/USD",
        session="london",
        llm_pair={
            "claude_bias": "NEUTRAL",
            "gpt4_bias": "NEUTRAL",
            "claude_confidence": "MEDIUM",
            "gpt4_confidence": "MEDIUM",
        },
    )

    assert out["ok"] is True
    assert out["agreement_flag"] == "agree"
    assert out["bias"] == "NEUTRAL"
    sw = dict(out.get("source_weights") or {})
    assert "claude" in sw and "gpt4" in sw
    assert float(sw["claude"]) > float(sw["gpt4"])


def test_no_llm_biases_returns_neutral_low(tmp_path):
    rt = _mk(tmp_path)

    out = rt.get_llm_weighted_bias(
        pair="EUR/USD",
        session="london",
        llm_pair={},
    )

    assert out["ok"] is True
    assert out["bias"] == "NEUTRAL"
    assert out["confidence"] == "LOW"
    assert out["agreement_flag"] == "none"
    assert out["avoid"] is False

def test_log_llm_accuracy_p3b_extended_fields_roundtrip(tmp_path):
    from backend.modules.aion_learning.llm_weighting_runtime import LLMWeightingRuntime, _iter_jsonl

    p = tmp_path / "llm_accuracy_log.jsonl"
    rt = LLMWeightingRuntime(accuracy_log_path=p)

    out = rt.log_llm_accuracy(
        llm_id="claude",
        pair="EURUSD",
        session="london",
        event_type="cpi",
        task_type="directional_bias",
        predicted_bias="BULLISH",
        actual_outcome_bias="BULLISH",
        confidence="HIGH",
        score=0.8,
        directional_bias_label="trend_continuation",
        level_prediction="breakout_above_range_high",
        level_actual="breakout_above_range_high",
        reaction_interpretation="news_spike_hold",
        actual_reaction_interpretation="news_spike_hold",
    )
    assert out["ok"] is True

    rows = _iter_jsonl(p)
    assert len(rows) == 1
    row = rows[0]

    assert row["directional_bias_label"] == "trend_continuation"
    assert row["level_prediction"] == "breakout_above_range_high"
    assert row["level_actual"] == "breakout_above_range_high"
    assert row["level_correct"] is True
    assert row["reaction_interpretation"] == "news_spike_hold"
    assert row["actual_reaction_interpretation"] == "news_spike_hold"
    assert row["reaction_correct"] is True


def test_summarize_llm_accuracy_includes_p3b_breakdowns(tmp_path):
    from backend.modules.aion_learning.llm_weighting_runtime import LLMWeightingRuntime

    p = tmp_path / "llm_accuracy_log.jsonl"
    rt = LLMWeightingRuntime(accuracy_log_path=p)

    rt.log_llm_accuracy(
        llm_id="claude",
        pair="EURUSD",
        session="LONDON",
        event_type="CPI",
        predicted_bias="BULLISH",
        actual_outcome_bias="BULLISH",
        level_prediction="breakout",
        level_actual="breakout",
        reaction_interpretation="spike_hold",
        actual_reaction_interpretation="spike_hold",
    )
    rt.log_llm_accuracy(
        llm_id="gpt4",
        pair="EURUSD",
        session="LONDON",
        event_type="CPI",
        predicted_bias="BEARISH",
        actual_outcome_bias="BULLISH",
        level_prediction="rejection",
        level_actual="breakout",
        reaction_interpretation="fade",
        actual_reaction_interpretation="spike_hold",
    )

    s = rt.summarize_llm_accuracy()
    assert s["ok"] is True
    assert s["matched_rows"] == 2
    assert "breakdowns" in s

    bd = s["breakdowns"]
    assert "counts" in bd
    assert "directional_correctness" in bd
    assert "level_prediction_correctness" in bd
    assert "reaction_interpretation_correctness" in bd

    # counts come back as list[tuple-like json arrays]
    pair_counts = dict(bd["counts"]["pair"])
    assert pair_counts.get("EURUSD") == 2

    # directional correctness by pair should be 1 correct / 1 incorrect
    by_pair = bd["directional_correctness"]["by_pair"]["EURUSD"]
    assert by_pair["n"] == 2
    assert by_pair["correct_n"] == 1
    assert by_pair["incorrect_n"] == 1
    assert float(by_pair["accuracy"]) == 0.5

    # level correctness by pair should also be 1/2
    lvl_by_pair = bd["level_prediction_correctness"]["by_pair"]["EURUSD"]
    assert lvl_by_pair["n"] == 2
    assert lvl_by_pair["correct_n"] == 1
    assert lvl_by_pair["incorrect_n"] == 1
    assert float(lvl_by_pair["accuracy"]) == 0.5

    # reaction correctness by pair should also be 1/2
    rxn_by_pair = bd["reaction_interpretation_correctness"]["by_pair"]["EURUSD"]
    assert rxn_by_pair["n"] == 2
    assert rxn_by_pair["correct_n"] == 1
    assert rxn_by_pair["incorrect_n"] == 1
    assert float(rxn_by_pair["accuracy"]) == 0.5


def test_review_llm_accuracy_ops_wrapper(tmp_path):
    from backend.modules.aion_learning.llm_weighting_runtime import LLMWeightingRuntime

    p = tmp_path / "llm_accuracy_log.jsonl"
    rt = LLMWeightingRuntime(accuracy_log_path=p)

    rt.log_llm_accuracy(
        llm_id="claude",
        pair="EURUSD",
        session="LONDON",
        event_type="CPI",
        predicted_bias="BULLISH",
        actual_outcome_bias="BULLISH",
        level_prediction="breakout",
        level_actual="breakout",
        reaction_interpretation="spike_hold",
        actual_reaction_interpretation="spike_hold",
        confidence="HIGH",
        score=0.9,
    )
    rt.log_llm_accuracy(
        llm_id="gpt4",
        pair="EURUSD",
        session="LONDON",
        event_type="CPI",
        predicted_bias="BEARISH",
        actual_outcome_bias="BULLISH",
        level_prediction="rejection",
        level_actual="breakout",
        reaction_interpretation="fade",
        actual_reaction_interpretation="spike_hold",
        confidence="LOW",
        score=-0.5,
    )

    out = rt.review_llm_accuracy(
        pair="EURUSD",
        session="LONDON",
        event_type="CPI",
        task_type="directional_bias",
        lookback_rows=100,
    )

    assert out["ok"] is True
    assert out["mode"] == "audit_review"
    assert out["schema_version"].startswith("aion.llm_weighting_runtime.")
    assert out["matched_rows"] == 2

    # passes through summary-compatible fields
    assert "per_llm" in out
    assert "breakdowns" in out
    assert "filters" in out

    # adds ops review payload
    assert "ops" in out
    ops = out["ops"]
    assert "topline" in ops
    assert "flags" in ops
    assert "recommendations" in ops

    topline = ops["topline"]
    assert topline["matched_rows"] == 2
    assert "llm_count" in topline
    assert topline["llm_count"] >= 1