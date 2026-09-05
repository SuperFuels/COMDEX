from __future__ import annotations

from backend.modules.aion_inference import SemanticGateway


def test_verified_profit_request_bypasses_model_with_proof():
    result = SemanticGateway().route(
        "What profit would we make if revenue is EUR 4000, materials are EUR 1700, "
        "and labour is EUR 900?"
    )

    assert result.route == "verified_atomsheet"
    assert result.model_call_required is False
    assert result.structured_result == {
        "profit": "1400",
        "margin_percent": "35",
        "currency": "EUR",
    }
    assert "1400 EUR" in result.answer
    assert result.proof_receipt["inverse_verified"] is True
    assert result.proof_receipt["model_calls"] == 0
    assert result.meaning_capsule.glyph_address.startswith("glyph:sha256:")


def test_natural_spend_wording_is_compiled_to_same_canonical_meaning():
    gateway = SemanticGateway()
    first = gateway.route(
        "Calculate profit: charged €4,000, spent €1,700 on materials and €900 on labour."
    )
    second = gateway.route(
        "Profit with revenue EUR 4000, materials EUR 1700 and labour EUR 900?"
    )
    assert first.route == "verified_atomsheet"
    assert second.route == "verified_atomsheet"
    assert first.meaning_capsule.glyph_address == second.meaning_capsule.glyph_address
    assert first.proof_receipt["result_sha256"] == second.proof_receipt["result_sha256"]


def test_field_parser_does_not_capture_preceding_fields_number():
    capsule = SemanticGateway().compile(
        "Profit if revenue is EUR 4000, materials are EUR 1700, and labour is EUR 900?"
    )
    assert capsule.entities == {"revenue": "4000", "materials": "1700", "labour": "900"}


def test_missing_input_falls_back_and_never_executes_partial_sheet():
    result = SemanticGateway().route("Calculate profit from EUR 4000 revenue and EUR 1700 materials.")
    assert result.route == "full_model"
    assert result.model_call_required is True
    assert result.answer is None
    assert result.proof_receipt["gate_reason"] == "required_inputs_incomplete"
    assert result.minimal_model_prompt


def test_mixed_currencies_are_ambiguous_and_cannot_bypass_model():
    result = SemanticGateway().route(
        "Calculate profit with revenue EUR 4000, materials GBP 1700 and labour EUR 900."
    )
    assert result.route == "full_model"
    assert result.meaning_capsule.ambiguity_score > 0
    assert result.proof_receipt["gate_reason"] == "meaning_is_ambiguous"


def test_policy_constraints_survive_compilation_and_fallback_prompt():
    result = SemanticGateway().route(
        "Prepare a quotation. Do not book anything, do not take payment, and human review is required."
    )
    assert result.route == "full_model"
    assert result.meaning_capsule.constraints == (
        "BOOKING_PROHIBITED",
        "HUMAN_REVIEW_REQUIRED",
        "PAYMENT_PROHIBITED",
    )
    assert "BOOKING_PROHIBITED" in result.minimal_model_prompt
    assert "PAYMENT_PROHIBITED" in result.minimal_model_prompt
    assert "HUMAN_REVIEW_REQUIRED" in result.minimal_model_prompt


def test_profit_bypass_rejects_positive_compound_action():
    result = SemanticGateway().route(
        "Calculate profit from revenue EUR 4000, materials EUR 1700 and labour EUR 900, then book the job."
    )
    assert result.route == "full_model"
    assert result.model_call_required is True
    assert result.proof_receipt["gate_reason"] == "compound_action_requires_orchestration"


def test_profit_bypass_allows_explicit_prohibition_without_dropping_constraint():
    result = SemanticGateway().route(
        "Calculate profit from revenue EUR 4000, materials EUR 1700 and labour EUR 900, and do not book anything."
    )
    assert result.route == "verified_atomsheet"
    assert result.meaning_capsule.constraints == ("BOOKING_PROHIBITED",)
