from backend.modules.aion_lrm.evidence_gap_envelope import (
    DEFAULT_REQUIRED_EVIDENCE,
    EVIDENCE_GAP_ENVELOPE_VERSION,
    build_default_home_fixed_evidence_gap_envelope,
    build_evidence_gap_envelope,
)
from backend.modules.aion_lrm.human_review_decision_envelope import (
    build_human_review_decision_envelope,
)


def test_phase20g_builds_default_evidence_gap_envelope():
    gap = build_default_home_fixed_evidence_gap_envelope()

    assert gap["envelope_version"] == EVIDENCE_GAP_ENVELOPE_VERSION
    assert gap["envelope_type"] == "aion_lrm_evidence_gap"
    assert gap["business_id"] == "home_fixed"
    assert gap["evidence_gap_hash"].startswith("evidence_gap_envelope_")
    assert gap["summary_hash"].startswith("evidence_gap_summary_")


def test_phase20g_default_gap_is_active_for_request_more_evidence():
    gap = build_default_home_fixed_evidence_gap_envelope()

    assert gap["gap_state"]["decision"] == "request_more_evidence"
    assert gap["gap_state"]["evidence_gap_active"] is True
    assert gap["gap_state"]["required_evidence"] == DEFAULT_REQUIRED_EVIDENCE
    assert gap["summary"]["missing_evidence_count"] >= 1


def test_phase20g_gap_links_back_to_decision_and_recommendation():
    gap = build_default_home_fixed_evidence_gap_envelope()

    assert gap["source_decision_envelope_hash"]
    assert gap["source_decision_summary_hash"]
    assert gap["gap_state"]["blocks_recommendation_card_hash"]
    assert gap["gap_state"]["blocks_recommendation_summary_hash"]


def test_phase20g_gap_can_be_inactive_for_approve_preview():
    decision = build_human_review_decision_envelope(decision="approve_preview")
    gap = build_evidence_gap_envelope(decision)

    assert gap["gap_state"]["decision"] == "approve_preview"
    assert gap["gap_state"]["evidence_gap_active"] is False


def test_phase20g_records_custom_required_evidence():
    decision = build_human_review_decision_envelope(
        decision="request_more_evidence",
        evidence_requested=["before_photo", "material_type"],
    )
    gap = build_evidence_gap_envelope(decision)

    assert gap["gap_state"]["required_evidence"] == ["before_photo", "material_type"]
    assert gap["gap_state"]["missing_evidence"] == ["before_photo", "material_type"]


def test_phase20g_redacts_private_reasoning_and_credentials():
    gap = build_evidence_gap_envelope({
        "business_id": "home_fixed",
        "envelope_hash": "decision_hash",
        "summary_hash": "decision_summary_hash",
        "decision_state": {"decision": "request_more_evidence"},
        "recommendation_card": {
            "card_hash": "card_hash",
            "summary_hash": "summary_hash",
            "private_chain_of_thought": "PRIVATE_COT_VALUE",
            "access_token": "ACCESS_TOKEN_VALUE",
        },
        "api_key": "API_KEY_VALUE",
        "hidden_reasoning": "HIDDEN_REASONING_VALUE",
    })

    text = str(gap)

    assert "PRIVATE_COT_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "API_KEY_VALUE" not in text
    assert "HIDDEN_REASONING_VALUE" not in text
    assert gap["safety"]["private_chain_of_thought_exposed"] is False
    assert gap["safety"]["hidden_reasoning_exposed"] is False
    assert gap["safety"]["credentials_exposed"] is False


def test_phase20g_blocks_all_live_side_effects():
    gap = build_default_home_fixed_evidence_gap_envelope()
    safety = gap["safety"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["evidence_request_sends_message"] is False
    assert safety["decision_grants_live_permission"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase20g_is_deterministic_for_same_inputs():
    decision = build_human_review_decision_envelope(
        decision="request_more_evidence",
        evidence_requested=["site_photo"],
    )

    one = build_evidence_gap_envelope(decision)
    two = build_evidence_gap_envelope(decision)

    assert one["evidence_gap_hash"] == two["evidence_gap_hash"]
    assert one["summary_hash"] == two["summary_hash"]
