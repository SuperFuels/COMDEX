from __future__ import annotations

import hashlib
from decimal import Decimal

import pytest

from backend.modules.aion_inference.learned_atomsheets import (
    LearnedAtomSheetStore,
    VerifiedModelOutcome,
)


def _response_hash(index: int) -> str:
    return hashlib.sha256(f"model-response-{index}".encode()).hexdigest()


def _store(tmp_path, **overrides) -> LearnedAtomSheetStore:
    return LearnedAtomSheetStore(
        tmp_path / "learning.sqlite3",
        tmp_path / "promoted",
        **overrides,
    )


def _observe_markup(store: LearnedAtomSheetStore, index: int, cost: str, percent: str) -> object:
    result = str(Decimal(cost) * (Decimal("1") + Decimal(percent) / Decimal("100")))
    return store.observe(VerifiedModelOutcome(
        intent="CALCULATE_MARKED_UP_PRICE",
        inputs={"cost": cost, "markup_percent": percent},
        result=result,
        verifier_id="decimal-reference-a" if index % 2 else "decimal-reference-b",
        model_id="qwen3:1.7b",
        response_sha256=_response_hash(index),
        human_approved=index == 5,
        created_at=f"2026-09-05T20:00:{index:02d}+00:00",
    ))


def test_verified_outcomes_are_quarantined_until_all_promotion_gates_pass(tmp_path):
    store = _store(tmp_path)
    fixtures = [("100", "10"), ("80", "25"), ("50", "20"), ("240", "15"), ("12", "50")]
    for index, values in enumerate(fixtures):
        decision = _observe_markup(store, index, *values)
        assert decision.status == "quarantined"
        assert decision.reason == "minimum_observations_not_met"
    assert store.promoted("CALCULATE_MARKED_UP_PRICE") is None


def test_unique_template_is_promoted_after_training_holdout_and_verifier_diversity(tmp_path):
    store = _store(tmp_path)
    fixtures = [("100", "10"), ("80", "25"), ("50", "20"), ("240", "15"), ("12", "50"), ("400", "7")]
    for index, values in enumerate(fixtures):
        decision = _observe_markup(store, index, *values)
    assert decision.status == "promoted"
    assert decision.reason == "automatic_promotion_gates_passed"
    assert decision.candidate_template_ids == ("increase_a_percent_b.v1",)
    assert decision.promoted_sheet["origin"] == "verified_model_outcomes"
    assert decision.promoted_sheet["promotion_evidence"]["holdout_observations"] == 2
    assert (tmp_path / "promoted" / "calculate.marked.up.price.v1.json").exists()


def test_promoted_sheet_executes_new_values_with_inverse_receipt_and_no_model(tmp_path):
    store = _store(tmp_path)
    fixtures = [("100", "10"), ("80", "25"), ("50", "20"), ("240", "15"), ("12", "50"), ("400", "7")]
    for index, values in enumerate(fixtures):
        _observe_markup(store, index, *values)
    result = store.execute("CALCULATE_MARKED_UP_PRICE", {"cost": "150", "markup_percent": "12"})
    assert result.route == "verified_learned_atomsheet"
    assert result.structured_result == {"value": "168"}
    assert result.model_call_required is False
    assert result.proof_receipt["inverse_verified"] is True
    assert result.proof_receipt["model_calls"] == 0


def test_unverified_outcomes_cannot_contribute_to_promotion(tmp_path):
    store = _store(tmp_path)
    for index in range(8):
        decision = store.observe(VerifiedModelOutcome(
            intent="CALCULATE_TOTAL",
            inputs={"left": str(index + 1), "right": str(index + 3)},
            result=str(index * 2 + 4),
            verifier_id=f"verifier-{index % 2}",
            model_id="model-a",
            response_sha256=_response_hash(index),
            verifier_passed=False,
        ))
    assert decision.observation_count == 0
    assert store.promoted("CALCULATE_TOTAL") is None


def test_one_verifier_is_not_enough_for_automatic_promotion(tmp_path):
    store = _store(tmp_path)
    for index in range(6):
        decision = store.observe(VerifiedModelOutcome(
            intent="CALCULATE_TOTAL",
            inputs={"left": str(index + 1), "right": str(index + 11)},
            result=str(index * 2 + 12),
            verifier_id="single-verifier",
            model_id="model-a",
            response_sha256=_response_hash(index),
        ))
    assert decision.status == "quarantined"
    assert decision.reason == "insufficient_verifier_diversity"


def test_duplicate_inputs_do_not_satisfy_diversity_gate(tmp_path):
    store = _store(tmp_path)
    for index in range(6):
        decision = store.observe(VerifiedModelOutcome(
            intent="CALCULATE_TOTAL",
            inputs={"left": "2", "right": "3"},
            result="5",
            verifier_id=f"verifier-{index % 2}",
            model_id="model-a",
            response_sha256=_response_hash(index),
            created_at=f"2026-09-05T21:00:{index:02d}+00:00",
        ))
    assert decision.reason == "insufficient_input_diversity"


def test_invalid_identifiers_hashes_and_numeric_bounds_are_rejected(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.observe(VerifiedModelOutcome(
            intent="free form intent",
            inputs={"a": "1", "b": "2"},
            result="3",
            verifier_id="v",
            model_id="m",
            response_sha256="not-a-hash",
        ))
    with pytest.raises(ValueError):
        store.observe(VerifiedModelOutcome(
            intent="CALCULATE_TOTAL",
            inputs={"left": "1e99", "right": "2"},
            result="3",
            verifier_id="v",
            model_id="m",
            response_sha256=_response_hash(1),
        ))


def test_execute_fails_closed_on_unknown_intent_or_input_mismatch(tmp_path):
    store = _store(tmp_path)
    missing = store.execute("UNKNOWN_CALCULATION", {"a": "1", "b": "2"})
    assert missing.route == "full_model"
    assert missing.proof_receipt["gate_reason"] == "no_promoted_atomsheet"


def test_status_and_audit_are_persistent(tmp_path):
    store = _store(tmp_path)
    _observe_markup(store, 0, "100", "10")
    status = store.status()
    assert status["verified_outcomes"] == 1
    assert status["candidate_intents"] == 1
    assert status["last_audit_sequence"] >= 2
    reopened = _store(tmp_path)
    assert reopened.status()["verified_outcomes"] == 1


def test_later_verified_outcome_monitors_without_rewriting_promoted_contract(tmp_path):
    store = _store(tmp_path)
    fixtures = [("100", "10"), ("80", "25"), ("50", "20"), ("240", "15"), ("12", "50"), ("400", "7")]
    for index, values in enumerate(fixtures):
        promoted = _observe_markup(store, index, *values)
    contract = promoted.contract_sha256
    later = _observe_markup(store, 9, "225", "16")
    assert later.status == "promoted"
    assert later.reason == "existing_promotion_still_validated"
    assert later.contract_sha256 == contract


def test_promoted_markup_sheet_routes_plain_english_and_rejects_compound_action(tmp_path):
    store = _store(tmp_path)
    fixtures = [("100", "10"), ("80", "25"), ("50", "20"), ("240", "15"), ("12", "50"), ("400", "7")]
    for index, values in enumerate(fixtures):
        _observe_markup(store, index, *values)
    result = store.route_text("What is 225 with a 16% markup?")
    assert result.route == "verified_learned_atomsheet"
    assert result.answer == "261"
    assert result.proof_receipt["normalized_inputs"] == {"cost": "225", "markup_percent": "16"}
    blocked = store.route_text("Add 16% markup to 225 and then send an invoice")
    assert blocked.route == "full_model"
    assert blocked.proof_receipt["gate_reason"] == "compound_action_requires_orchestration"
    multiple = store.route_text("Apply 16% markup to 225 and also 5% tax")
    assert multiple.route == "full_model"
    assert multiple.proof_receipt["gate_reason"] == "learned_text_numeric_ambiguity"
    negative = store.route_text("Apply 16% markup to -225")
    assert negative.route == "full_model"
