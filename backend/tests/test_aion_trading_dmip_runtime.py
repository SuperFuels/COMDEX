from __future__ import annotations

from typing import Any, Dict

import pytest

from backend.modules.aion_trading import dmip_runtime


def _pair_row(result: Dict[str, Any], pair: str) -> Dict[str, Any]:
    rows = (
        result.get("bias_sheet", {})
        .get("pair_biases", [])
    )
    for row in rows:
        if isinstance(row, dict) and row.get("pair") == pair:
            return row
    raise AssertionError(f"pair row not found: {pair}")


def test_dmip_checkpoint_disagreement_preserved_as_avoid():
    result = dmip_runtime.run_dmip_checkpoint(
        checkpoint="pre_market",
        market_snapshot={"pairs": ["EUR/USD"]},
        llm_consultation={
            "pairs": {
                "EUR/USD": {
                    "claude_bias": "BULLISH",
                    "gpt4_bias": "BEARISH",
                    "confidence": "HIGH",
                    "key_levels": [1.08, 1.085],
                }
            }
        },
    )

    assert result["ok"] is True
    row = _pair_row(result, "EUR/USD")
    assert row["bias"] == "AVOID"
    assert row["confidence"] == "LOW"

    flags = result["bias_sheet"]["llm_agreement_flags"]
    assert flags["EUR/USD"] == "disagree"

    hints = result.get("llm_weighted_hints", {})
    assert "EUR/USD" in hints
    # If runtime unavailable, still additive/fail-open; if available, disagreement should remain preserved
    if hints["EUR/USD"].get("ok"):
        assert hints["EUR/USD"]["agreement"] in {"disagree", "unavailable", "partial"}

    notes = result.get("notes", [])
    assert "disagreement_preserved_as_signal" in notes
    assert "risk_invariants_not_mutated" in notes


def test_dmip_checkpoint_agreement_returns_weighted_hints_key_and_learning_events():
    result = dmip_runtime.run_dmip_checkpoint(
        checkpoint="london",
        market_snapshot={"pairs": ["GBP/USD"]},
        llm_consultation={
            "pairs": {
                "GBP/USD": {
                    "claude_bias": "BULLISH",
                    "gpt4_bias": "BULLISH",
                    "confidence": "MEDIUM",
                    "key_levels": [1.25, "1.2550", "bad"],
                }
            }
        },
    )

    assert result["ok"] is True

    row = _pair_row(result, "GBP/USD")
    assert row["bias"] in {"BULLISH", "AVOID", "NEUTRAL", "BEARISH"}  # contract-safe
    assert row["confidence"] in {"HIGH", "MEDIUM", "LOW"}

    # additive outputs always present (Phase 3)
    assert "llm_weighted_hints" in result
    assert "learning_events" in result
    assert "decision_influence_weighting" in result

    hints = result["llm_weighted_hints"]
    assert "GBP/USD" in hints
    assert isinstance(hints["GBP/USD"], dict)

    learning = result["learning_events"]
    assert "llm_accuracy" in learning
    assert "task_tracking" in learning
    assert isinstance(learning["llm_accuracy"], list)
    assert isinstance(learning["task_tracking"], list)
    # With llm input present, stubs should normally emit entries
    assert len(learning["llm_accuracy"]) >= 1
    assert len(learning["task_tracking"]) >= 1

    weighting = result["decision_influence_weighting"]
    assert "scope" in weighting
    assert "loaded" in weighting
    assert "notes" in weighting

    meta = result["bias_sheet"]["metadata"]
    assert meta.get("risk_invariants_mutated") is False
    assert "decision_influence_weighting_loaded" in meta
    assert "decision_influence_weighting_notes" in meta


def test_dmip_checkpoint_weights_runtime_unavailable_is_fail_open(monkeypatch: pytest.MonkeyPatch):
    # Force runtime unavailable/init error path
    monkeypatch.setattr(
        dmip_runtime,
        "get_decision_influence_runtime",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        raising=False,
    )

    result = dmip_runtime.run_dmip_checkpoint(
        checkpoint="new_york",
        market_snapshot={"pairs": ["USD/JPY"]},
        llm_consultation={
            "pairs": {
                "USD/JPY": {
                    "claude_bias": "NEUTRAL",
                    "gpt4_bias": "NEUTRAL",
                    "confidence": "LOW",
                }
            }
        },
    )

    assert result["ok"] is True  # fail-open, non-breaking

    weighting = result["decision_influence_weighting"]
    assert weighting["loaded"] is False
    assert isinstance(weighting["notes"], list)
    assert any("decision_influence_runtime_init_error" in str(x) for x in weighting["notes"])

    # Primary DMIP output still valid
    row = _pair_row(result, "USD/JPY")
    assert row["bias"] in {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"}
    assert row["confidence"] in {"HIGH", "MEDIUM", "LOW"}

    meta = result["bias_sheet"]["metadata"]
    assert meta.get("risk_invariants_mutated") is False