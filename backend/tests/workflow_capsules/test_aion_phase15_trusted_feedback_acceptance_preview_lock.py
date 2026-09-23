from pathlib import Path

from backend.modules.aion.axo.axo_ets_contracts import (
    TRUSTED_FEEDBACK_ACCEPTANCE_VERSION,
    build_ets_feedback_packet_preview,
    build_trusted_feedback_acceptance_preview,
)

APP = Path("desktop/mac/src/app.js")


def _app_text() -> str:
    return APP.read_text()


def test_phase15e_builds_trusted_feedback_acceptance_preview():
    packet = build_ets_feedback_packet_preview()
    preview = build_trusted_feedback_acceptance_preview(packet)

    assert preview["acceptance_version"] == TRUSTED_FEEDBACK_ACCEPTANCE_VERSION
    assert preview["preview_only"] is True
    assert preview["human_review_required"] is True
    assert preview["trusted_feedback_acceptance_hash"]


def test_phase15e_unverified_signature_is_not_eligible_for_review():
    packet = build_ets_feedback_packet_preview(signature_preview="unsigned")
    preview = build_trusted_feedback_acceptance_preview(
        packet,
        operator_decision="eligible_for_human_review",
    )

    assert preview["eligible_for_human_review"] is False
    assert preview["acceptance_status"] == "rejected_preview"
    assert "signature_not_verified" in preview["blocking_reasons"]


def test_phase15e_verified_clean_packet_can_be_marked_eligible_for_human_review():
    packet = build_ets_feedback_packet_preview()
    packet["external_agent"]["signature_verified"] = True

    preview = build_trusted_feedback_acceptance_preview(
        packet,
        operator_decision="eligible_for_human_review",
    )

    assert preview["eligible_for_human_review"] is True
    assert preview["acceptance_status"] == "eligible_for_human_review"
    assert preview["operator_decision"] == "eligible_for_human_review"


def test_phase15e_acceptance_preview_never_mutates_live_state():
    packet = build_ets_feedback_packet_preview()
    packet["external_agent"]["signature_verified"] = True

    preview = build_trusted_feedback_acceptance_preview(
        packet,
        operator_decision="eligible_for_human_review",
    )

    side_effects = preview["side_effects"]
    assert side_effects["reputation_mutation"] is False
    assert side_effects["trust_score_mutation"] is False
    assert side_effects["public_trust_state_mutation"] is False
    assert side_effects["booking_created"] is False
    assert side_effects["payment_created"] is False
    assert side_effects["escrow_created"] is False
    assert side_effects["external_message_sent"] is False


def test_phase15e_score_separation_is_preserved_in_acceptance_packet():
    preview = build_trusted_feedback_acceptance_preview()

    accepted = preview["accepted_packet"]
    separation = accepted["score_separation"]

    assert "customer_outcome_score" in accepted["scores"]
    assert "system_execution_score" in accepted["scores"]
    assert separation["must_not_merge_customer_and_system_scores"] is True


def test_phase15e_frontend_panel_function_and_mount_exist():
    text = _app_text()

    assert "function renderTrustedFeedbackAcceptancePanel()" in text
    assert "${renderTrustedFeedbackAcceptancePanel()}" in text
    assert 'data-axo-trusted-feedback-acceptance-panel="true"' in text


def test_phase15e_frontend_buttons_are_visible_and_wired():
    text = _app_text()

    for term in [
        "Mark eligible for human review",
        "Reject preview",
        "Reset pending",
        'data-axo-feedback-action="mark-review"',
        'data-axo-feedback-action="reject-preview"',
        'data-axo-feedback-action="reset-pending"',
        "handleTrustedFeedbackPreviewDecision",
    ]:
        assert term in text


def test_phase15e_frontend_shows_side_effect_boundary():
    text = _app_text()

    for term in [
        "Side-effect boundary",
        "Reputation mutation",
        "Trust score mutation",
        "Public trust state mutation",
        "Booking created",
        "Payment created",
        "Escrow created",
        "External message sent",
    ]:
        assert term in text


def test_phase15e_frontend_does_not_enable_live_mutation_functions():
    text = _app_text()

    forbidden = [
        "mutateReputation(",
        "writeTrustScore(",
        "publishPublicTrustState(",
        "createBooking(",
        "capturePayment(",
        "releaseEscrow(",
        "sendExternalMessage(",
    ]

    for item in forbidden:
        assert item not in text
