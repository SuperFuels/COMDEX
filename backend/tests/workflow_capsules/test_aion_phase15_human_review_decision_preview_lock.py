from backend.modules.aion.axo.axo_ets_contracts import (
    build_axo_human_review_decision_preview,
    build_ets_feedback_packet_preview,
)


APP = "desktop/mac/src/app.js"


def _app_text() -> str:
    from pathlib import Path

    return Path(APP).read_text()


def test_phase15f_builds_human_review_decision_preview_contract():
    preview = build_axo_human_review_decision_preview()

    assert preview["decision_preview_version"] == "aion.axo_human_review_decision_preview.v0.1"
    assert preview["preview_only"] is True
    assert preview["human_review_required"] is True
    assert preview["automated_decision_allowed"] is False
    assert preview["requested_decision"] in {
        "accept",
        "reject",
        "request_more_evidence",
    }


def test_phase15f_supports_accept_reject_and_request_more_evidence_preview_states():
    for decision in ["accept", "reject", "request_more_evidence"]:
        preview = build_axo_human_review_decision_preview(requested_decision=decision)
        assert preview["requested_decision"] == decision
        assert preview["decision"] == decision
        assert preview["preview_only"] is True


def test_phase15f_requires_eligible_feedback_before_decision_preview():
    packet = build_ets_feedback_packet_preview(signature_preview="signature_preview_unverified")
    preview = build_axo_human_review_decision_preview(packet)

    assert preview["eligible_for_human_review"] is False
    assert "not_eligible_for_human_review" in preview["blocking_reasons"]


def test_phase15f_verified_clean_packet_can_enter_human_review_decision_preview():
    packet = build_ets_feedback_packet_preview(
        signature_preview="signed-preview",
        proof_receipt_id="proof_receipt_001",
        job_trace_id="job_trace_001",
        evidence_ids=["evidence_001"],
    )
    packet["external_agent"]["signature_verified"] = True

    preview = build_axo_human_review_decision_preview(packet, requested_decision="accept")

    assert preview["eligible_for_human_review"] is True
    assert preview["requested_decision"] == "accept"
    assert preview["human_review_required"] is True
    assert preview["automated_decision_allowed"] is False


def test_phase15f_preserves_customer_and_system_score_separation():
    preview = build_axo_human_review_decision_preview()
    separation = preview["packet"]["score_separation"]

    assert separation["customer_outcome_score_is_customer_signal"] is True
    assert separation["system_execution_score_is_machine_execution_signal"] is True
    assert separation["must_not_merge_customer_and_system_scores"] is True


def test_phase15f_blocks_all_live_side_effects():
    preview = build_axo_human_review_decision_preview()
    guards = preview["side_effect_guards"]

    assert guards["reputation_mutation_allowed"] is False
    assert guards["public_trust_update_allowed"] is False
    assert guards["booking_side_effect_allowed"] is False
    assert guards["payment_side_effect_allowed"] is False
    assert guards["escrow_side_effect_allowed"] is False
    assert guards["external_message_side_effect_allowed"] is False
    assert guards["live_execution_allowed"] is False


def test_phase15f_frontend_panel_is_visible_and_mounted():
    text = _app_text()

    assert "function renderAxoHumanReviewDecisionPreviewPanel()" in text
    assert "${renderAxoHumanReviewDecisionPreviewPanel()}" in text
    assert "Human Review Decision Preview" in text
    assert 'data-axo-human-review-decision-preview="true"' in text
    assert "accept, reject, or request-more-evidence" in text


def test_phase15f_frontend_exposes_decision_states_and_score_separation():
    text = _app_text()

    assert 'data-axo-decision-states="true"' in text
    assert 'data-axo-score-separation="true"' in text
    assert "Accept preview" in text
    assert "Reject preview" in text
    assert "Request more evidence" in text
    assert "Customer outcome score" in text
    assert "System execution score" in text
    assert "Must not merge" in text


def test_phase15f_frontend_exposes_side_effect_guards():
    text = _app_text()

    assert 'data-axo-decision-side-effect-guards="true"' in text
    for phrase in [
        "Reputation mutation allowed",
        "Public trust update allowed",
        "Booking side effect allowed",
        "Payment side effect allowed",
        "Escrow side effect allowed",
        "External message side effect allowed",
        "Live execution allowed",
    ]:
        assert phrase in text
