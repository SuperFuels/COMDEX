# /workspaces/COMDEX/backend/tests/test_aion_trading_dmip_llm_synthesis.py
from __future__ import annotations

from typing import Any, Dict

from backend.modules.aion_trading import dmip_llm_synthesis as syn


def _weights_snapshot(
    *,
    claude: float = 1.0,
    gpt4: float = 1.0,
    version: int = 3,
    snapshot_hash: str = "abc123",
) -> Dict[str, Any]:
    return {
        "weights_version": version,
        "snapshot_hash": snapshot_hash,
        "llm_trust_weights": {
            "claude": claude,
            "gpt4": gpt4,
        },
    }


def test_get_llm_weighted_bias_disagreement_preserved_as_avoid() -> None:
    out = syn.get_llm_weighted_bias(
        pair="EUR/USD",
        llm_pair={
            "claude_bias": "BULLISH",
            "gpt4_bias": "BEARISH",
            "confidence": "HIGH",
        },
        weights_snapshot=_weights_snapshot(claude=1.4, gpt4=1.6),
        base_selected_bias="BULLISH",
        base_confidence="HIGH",
    )

    assert out["ok"] is True
    assert out["pair"] == "EUR/USD"
    assert out["agreement"] == "disagree"
    assert out["weighted_bias"] == "AVOID"
    assert out["weighted_confidence"] == "LOW"
    assert out["reason"] == "llm_disagreement_preserved"
    assert out["risk_invariants_mutated"] is False
    assert out["non_blocking"] is True
    assert out["weights_version"] == 3
    assert out["snapshot_hash"] == "abc123"


def test_get_llm_weighted_bias_agreement_can_uplift_confidence_bounded() -> None:
    out = syn.get_llm_weighted_bias(
        pair="GBP/USD",
        llm_pair={
            "claude_bias": "BULLISH",
            "gpt4_bias": "BULLISH",
            "confidence": "MEDIUM",
        },
        weights_snapshot=_weights_snapshot(claude=1.6, gpt4=1.5),
        base_selected_bias="BULLISH",
        base_confidence="MEDIUM",
    )

    assert out["ok"] is True
    assert out["agreement"] == "agree"
    assert out["weighted_bias"] == "BULLISH"
    # avg = 1.55 => MEDIUM -> HIGH uplift path
    assert out["weighted_confidence"] == "HIGH"
    assert out["reason"] == "llm_agreement_weighted_hint"
    assert out["llm_weights_used"]["claude"] == 1.6
    assert out["llm_weights_used"]["gpt4"] == 1.5
    assert out["risk_invariants_mutated"] is False


def test_get_llm_weighted_bias_partial_when_missing_one_side() -> None:
    out = syn.get_llm_weighted_bias(
        pair="USD/JPY",
        llm_pair={
            "claude_bias": "BEARISH",
            # gpt4 missing
            "confidence": "LOW",
        },
        weights_snapshot=_weights_snapshot(),
        base_selected_bias="NEUTRAL",
        base_confidence="LOW",
    )

    assert out["ok"] is True
    assert out["agreement"] == "partial"
    assert out["weighted_bias"] is None
    assert out["weighted_confidence"] is None
    assert out["reason"] == "insufficient_llm_pair_data"
    assert out["risk_invariants_mutated"] is False


def test_get_llm_weighted_bias_fail_open_when_weights_snapshot_missing() -> None:
    out = syn.get_llm_weighted_bias(
        pair="EUR/USD",
        llm_pair={
            "claude_bias": "BULLISH",
            "gpt4_bias": "BULLISH",
            "confidence": "MEDIUM",
        },
        weights_snapshot=None,
        base_selected_bias="BULLISH",
        base_confidence="MEDIUM",
    )

    assert out["ok"] is False
    assert out["agreement"] == "unavailable"
    assert out["reason"] == "weights_snapshot_unavailable"
    assert out["weighted_bias"] is None
    assert out["weighted_confidence"] is None
    assert out["non_blocking"] is True
    assert out["risk_invariants_mutated"] is False


def test_synthesise_llm_consultation_batch_counts_and_per_pair() -> None:
    out = syn.synthesise_llm_consultation(
        llm_consultation={
            "pairs": {
                "EUR/USD": {
                    "claude_bias": "BULLISH",
                    "gpt4_bias": "BEARISH",
                    "confidence": "HIGH",
                },
                "GBP/USD": {
                    "claude_bias": "BULLISH",
                    "gpt4_bias": "BULLISH",
                    "confidence": "MEDIUM",
                },
                "USD/JPY": {
                    "claude_bias": "NEUTRAL",
                    # partial
                    "confidence": "LOW",
                },
            }
        },
        weights_snapshot=_weights_snapshot(claude=1.3, gpt4=1.2, version=7, snapshot_hash="snap7"),
        base_pair_outputs={
            "EUR/USD": {"bias": "AVOID", "confidence": "LOW"},
            "GBP/USD": {"bias": "BULLISH", "confidence": "MEDIUM"},
            "USD/JPY": {"bias": "NEUTRAL", "confidence": "LOW"},
        },
    )

    assert out["ok"] is True
    assert out["schema_version"] == "aion.dmip_llm_synthesis_result.v1"
    assert out["non_blocking"] is True
    assert out["risk_invariants_mutated"] is False
    assert out["weights_snapshot_loaded"] is True
    assert out["weights_version"] == 7
    assert out["snapshot_hash"] == "snap7"

    counts = out["counts"]
    assert counts["total_pairs_seen"] == 3
    assert counts["pairs_with_llm_payload"] == 3
    assert counts["agree"] == 1
    assert counts["disagree"] == 1
    assert counts["partial"] == 1
    assert counts["unavailable"] == 0
    assert counts["ok_results"] == 3
    assert counts["not_ok_results"] == 0

    per_pair = out["per_pair"]
    assert per_pair["EUR/USD"]["agreement"] == "disagree"
    assert per_pair["EUR/USD"]["weighted_bias"] == "AVOID"
    assert per_pair["GBP/USD"]["agreement"] == "agree"
    assert per_pair["USD/JPY"]["agreement"] == "partial"


def test_synthesise_llm_consultation_fail_open_without_weights_snapshot() -> None:
    out = syn.synthesise_llm_consultation(
        llm_consultation={
            "pairs": {
                "EUR/USD": {
                    "claude_bias": "BULLISH",
                    "gpt4_bias": "BULLISH",
                    "confidence": "MEDIUM",
                },
                "GBP/USD": {
                    "claude_bias": "BEARISH",
                    "gpt4_bias": "BEARISH",
                    "confidence": "LOW",
                },
            }
        },
        weights_snapshot=None,
    )

    assert out["ok"] is True  # batch function itself is fail-open and structured
    assert out["weights_snapshot_loaded"] is False
    assert out["risk_invariants_mutated"] is False

    counts = out["counts"]
    assert counts["total_pairs_seen"] == 2
    assert counts["unavailable"] == 2
    assert counts["not_ok_results"] == 2
    assert counts["ok_results"] == 0

    assert out["per_pair"]["EUR/USD"]["ok"] is False
    assert out["per_pair"]["EUR/USD"]["agreement"] == "unavailable"
    assert out["per_pair"]["GBP/USD"]["ok"] is False
    assert out["per_pair"]["GBP/USD"]["agreement"] == "unavailable"