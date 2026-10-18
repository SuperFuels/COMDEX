import pytest

from backend.modules.aion_lrm.human_review_decision_envelope import (
    ALLOWED_DECISIONS,
    HUMAN_REVIEW_DECISION_ENVELOPE_VERSION,
    build_default_home_fixed_human_review_decision_envelope,
    build_human_review_decision_envelope,
)


def test_phase20f_builds_default_decision_envelope():
    envelope = build_default_home_fixed_human_review_decision_envelope()

    assert envelope["envelope_version"] == HUMAN_REVIEW_DECISION_ENVELOPE_VERSION
    assert envelope["envelope_type"] == "aion_lrm_human_review_decision"
    assert envelope["business_id"] == "home_fixed"
    assert envelope["envelope_hash"].startswith("human_review_decision_envelope_")
    assert envelope["summary_hash"].startswith("human_review_decision_summary_")


def test_phase20f_allowed_decisions_are_locked():
    assert ALLOWED_DECISIONS == {
        "approve_preview",
        "reject",
        "request_more_evidence",
    }


def test_phase20f_rejects_unknown_decision():
    with pytest.raises(ValueError):
        build_human_review_decision_envelope(decision="approve_live_payment")


def test_phase20f_approve_preview_does_not_grant_live_permission():
    envelope = build_human_review_decision_envelope(decision="approve_preview")

    assert envelope["decision_state"]["decision"] == "approve_preview"
    assert envelope["decision_state"]["approval_scope"] == "preview_only"
    assert envelope["safety"]["decision_grants_live_permission"] is False
    assert envelope["summary"]["decision_grants_live_permission"] is False


def test_phase20f_request_more_evidence_records_evidence_request():
    envelope = build_human_review_decision_envelope(
        decision="request_more_evidence",
        evidence_requested=["site_photo", "roof_measurements"],
    )

    assert envelope["decision_state"]["decision"] == "request_more_evidence"
    assert envelope["decision_state"]["evidence_requested"] == [
        "site_photo",
        "roof_measurements",
    ]


def test_phase20f_links_recommendation_card_hashes():
    envelope = build_default_home_fixed_human_review_decision_envelope()

    assert envelope["recommendation_card_hash"]
    assert envelope["recommendation_summary_hash"]
    assert envelope["summary"]["recommendation_card_hash"] == envelope["recommendation_card_hash"]


def test_phase20f_blocks_all_live_side_effects():
    envelope = build_human_review_decision_envelope(decision="approve_preview")
    safety = envelope["safety"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase20f_redacts_private_reasoning_and_credentials():
    envelope = build_human_review_decision_envelope(
        recommendation_card={
            "business_id": "home_fixed",
            "card_hash": "card_hash",
            "summary_hash": "summary_hash",
            "private_chain_of_thought": "PRIVATE_COT_VALUE",
            "hidden_reasoning": "HIDDEN_REASONING_VALUE",
            "access_token": "ACCESS_TOKEN_VALUE",
            "api_key": "API_KEY_VALUE",
        }
    )

    text = str(envelope)

    assert "PRIVATE_COT_VALUE" not in text
    assert "HIDDEN_REASONING_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "API_KEY_VALUE" not in text
    assert envelope["safety"]["private_chain_of_thought_exposed"] is False
    assert envelope["safety"]["hidden_reasoning_exposed"] is False
    assert envelope["safety"]["credentials_exposed"] is False


def test_phase20f_is_deterministic_for_same_inputs():
    one = build_human_review_decision_envelope(decision="reject", reviewer_note="Not enough evidence.")
    two = build_human_review_decision_envelope(decision="reject", reviewer_note="Not enough evidence.")

    assert one["envelope_hash"] == two["envelope_hash"]
    assert one["summary_hash"] == two["summary_hash"]
