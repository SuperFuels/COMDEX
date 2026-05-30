from pathlib import Path

from backend.modules.aion.axo.axo_ets_contracts import (
    AXO_SCORING_VOCABULARY,
    build_ets_feedback_packet_preview,
    build_ets_agentmap_preview,
    build_axo_readiness_dashboard_preview,
    build_axo_trust_rule_lock_preview,
    build_axo_anti_gaming_agentmap_extension,
    build_trusted_feedback_acceptance_preview,
    build_axo_human_review_decision_preview,
    validate_ets_feedback_packet_preview,
)

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")
DOC = Path("docs/rfc/aion_phase15_axo_ets_consolidation_closeout_lock.tex")


def test_phase15g_scoring_vocabulary_and_ets_packet_are_locked():
    vocab = AXO_SCORING_VOCABULARY
    packet = build_ets_feedback_packet_preview()

    assert vocab["version"] == "aion.axo_scoring_vocabulary.v0.1"
    assert vocab["required_boundaries"]["preview_only"] is True
    assert vocab["required_boundaries"]["customer_outcome_separate_from_system_execution"] is True

    assert packet["packet_version"] == "aion.ets_feedback_packet.v0.1"
    assert packet["preview_only"] is True
    assert packet["live_reputation_mutation_allowed"] is False
    assert packet["score_separation"]["must_not_merge_customer_and_system_scores"] is True
    assert packet["trace_links"]["proof_receipt_id"]
    assert packet["trace_links"]["job_trace_id"]
    assert packet["trace_links"]["evidence_ids"]


def test_phase15g_feedback_validation_and_agentmap_preview_are_locked():
    packet = build_ets_feedback_packet_preview()
    validation = validate_ets_feedback_packet_preview(packet)
    agentmap_preview = build_ets_agentmap_preview(packet)

    assert validation["ok"] is True
    assert validation["preview_only"] is True

    assert agentmap_preview["agentmap_extension"] == "aion.ets_preview.v0.1"
    assert agentmap_preview["preview_only"] is True

    ets = agentmap_preview["execution_trust_score_preview"]
    assert ets["live_reputation_mutation_allowed"] is False
    assert ets["human_review_required"] is True


def test_phase15g_readiness_dashboard_and_anti_gaming_are_locked():
    dashboard = build_axo_readiness_dashboard_preview()
    lock = build_axo_trust_rule_lock_preview()
    extension = build_axo_anti_gaming_agentmap_extension()

    assert dashboard["dashboard_version"] == "aion.axo_readiness_dashboard.v0.1"
    assert dashboard["preview_only"] is True

    dashboard_text = str(dashboard)
    assert "live_reputation_mutation_allowed" in dashboard_text
    assert "False" in dashboard_text
    assert "human_review" in dashboard_text

    assert lock["lock_version"] == "aion.axo_trust_rule_lock.v0.1"
    assert lock["preview_only"] is True
    assert lock["anti_gaming_locked"] is True
    assert lock["trust_rules_locked"] is True
    assert lock["live_reputation_mutation_allowed"] is False

    assert extension["agentmap_extension"] == "aion.axo_anti_gaming_preview.v0.1"
    assert extension["preview_only"] is True
    assert extension["anti_gaming_locked"] is True
    assert extension["trust_rules_locked"] is True


def test_phase15g_trusted_feedback_and_human_review_decision_are_locked():
    packet = build_ets_feedback_packet_preview(signature_preview="signed-preview")
    packet["external_agent"]["signature_verified"] = True

    acceptance = build_trusted_feedback_acceptance_preview(packet)
    decision = build_axo_human_review_decision_preview(packet, requested_decision="accept")

    assert acceptance["acceptance_version"] == "aion.trusted_feedback_acceptance.v0.1"
    assert acceptance["preview_only"] is True
    assert acceptance["eligible_for_human_review"] is True

    side_effects = acceptance["side_effects"]
    assert side_effects["reputation_mutation"] is False
    assert side_effects["public_trust_state_mutation"] is False
    assert side_effects["booking_created"] is False
    assert side_effects["payment_created"] is False
    assert side_effects["escrow_created"] is False

    assert decision["decision_preview_version"] == "aion.axo_human_review_decision_preview.v0.1"
    assert decision["preview_only"] is True
    assert decision["human_review_required"] is True
    assert decision["requested_decision"] == "accept"
    assert decision["eligible_for_human_review"] is True

    guards = decision["side_effect_guards"]
    assert guards["reputation_mutation_allowed"] is False
    assert guards["public_trust_update_allowed"] is False
    assert guards["booking_side_effect_allowed"] is False
    assert guards["payment_side_effect_allowed"] is False
    assert guards["escrow_side_effect_allowed"] is False
    assert guards["external_message_side_effect_allowed"] is False


def test_phase15g_boardroom_frontend_surfaces_are_mounted():
    text = APP.read_text()

    assert "function renderAxoReadinessDashboardPanel()" in text
    assert "function renderAxoHumanReviewDecisionPreviewPanel()" in text
    assert "${renderAxoReadinessDashboardPanel()}" in text
    assert "${renderAxoHumanReviewDecisionPreviewPanel()}" in text

    # Phase 15E acceptance panel naming may be exact or embedded under AXO/ETS section.
    assert "Trusted Feedback Acceptance" in text
    assert "eligible_for_human_review" in text

    for label in [
        "AXO Readiness Dashboard",
        "Human Review Decision Preview",
        "Preview only",
        "No reputation mutation",
        "No booking",
        "No payment",
    ]:
        assert label in text

    # Public trust and escrow blocking are present in the locked frontend payload/guards
    # even if the visible labels are phrased differently.
    assert "public_trust" in text
    assert "escrow" in text


def test_phase15g_phase15_tests_are_in_focused_suite():
    text = SUITE.read_text()

    for test_file in [
        "test_aion_phase15_axo_ets_contract_foundation_lock.py",
        "test_aion_phase15_ets_agentmap_preview_lock.py",
        "test_aion_phase15_axo_readiness_dashboard_lock.py",
        "test_aion_phase15_axo_anti_gaming_trust_rule_lock.py",
        "test_aion_phase15_trusted_feedback_acceptance_preview_lock.py",
        "test_aion_phase15_human_review_decision_preview_lock.py",
        "test_aion_phase15_axo_ets_consolidation_closeout_lock.py",
    ]:
        assert test_file in text


def test_phase15g_latex_closeout_doc_exists_and_records_closed_status():
    text = DOC.read_text()

    for phrase in [
        "Phase 15G",
        "AXO + Execution Trust Score",
        "CLOSED",
        "preview-only",
        "anti-gaming",
        "trust-rule",
        "human review",
        "no reputation mutation",
        "no booking",
        "no payment",
        "no escrow",
        "Lock ID:",
        "Status:",
        "Maintainer: Tessaris AI",
        "Author: Kevin Robinson",
    ]:
        assert phrase in text
