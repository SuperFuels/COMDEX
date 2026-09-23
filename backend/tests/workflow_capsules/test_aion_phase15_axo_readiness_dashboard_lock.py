from backend.modules.aion.axo.axo_ets_contracts import (
    build_axo_readiness_dashboard_preview,
    build_ets_feedback_packet_preview,
)

from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _app_text() -> str:
    return APP.read_text()


def test_phase15c_builds_preview_only_axo_readiness_dashboard():
    packet = build_ets_feedback_packet_preview(
        customer_outcome_score=80,
        system_execution_score=60,
        agent_reliability_score=40,
        evidence_quality_score=20,
    )

    dashboard = build_axo_readiness_dashboard_preview(packet)

    assert dashboard["dashboard_version"] == "aion.axo_readiness_dashboard.v0.1"
    assert dashboard["preview_only"] is True
    assert dashboard["readiness_score_preview"] == 50
    assert dashboard["safety"]["read_only"] is True


def test_phase15c_dashboard_separates_customer_and_system_scores():
    dashboard = build_axo_readiness_dashboard_preview()

    assert "customer_outcome_score" in dashboard["score_classes"]
    assert "system_execution_score" in dashboard["score_classes"]
    assert dashboard["score_separation"]["must_not_merge_customer_and_system_scores"] is True


def test_phase15c_dashboard_links_to_evidence_proof_and_job_trace():
    dashboard = build_axo_readiness_dashboard_preview()
    links = dashboard["trace_links"]

    assert links["job_trace_id"]
    assert links["proof_receipt_id"]
    assert links["evidence_ids"]
    assert links["ets_feedback_hash"]


def test_phase15c_dashboard_keeps_trust_controls_locked():
    dashboard = build_axo_readiness_dashboard_preview()
    controls = dashboard["trust_controls"]

    assert controls["anti_gaming_locked"] is False
    assert controls["trust_rules_locked"] is False
    assert controls["human_review_required"] is True
    assert controls["live_reputation_mutation_allowed"] is False
    assert controls["public_ranking_enabled"] is False


def test_phase15c_dashboard_reports_blockers_until_governance_locked():
    dashboard = build_axo_readiness_dashboard_preview()

    assert "external_agent_signature_not_verified" in dashboard["blockers"]
    assert "anti_gaming_rules_not_locked" in dashboard["blockers"]
    assert "trust_rules_not_locked" in dashboard["blockers"]


def test_phase15c_frontend_renders_axo_readiness_panel():
    text = _app_text()

    assert "function renderAxoReadinessDashboardPanel()" in text
    assert "${renderAxoReadinessDashboardPanel()}" in text
    assert "AXO Readiness Dashboard" in text
    assert 'data-axo-readiness-dashboard-panel="true"' in text


def test_phase15c_frontend_exposes_required_visible_sections():
    text = _app_text()

    for phrase in [
        "AXO + Execution Trust Score",
        "Readiness score",
        "Customer outcome",
        "System execution",
        "Evidence quality",
        "Score separation",
        "Trust controls",
        "Evidence / proof links",
        "Readiness blockers",
    ]:
        assert phrase in text


def test_phase15c_frontend_safety_boundary_blocks_live_side_effects():
    text = _app_text()
    panel_start = text.find("function renderAxoReadinessDashboardPanel")
    panel_end = text.find("/* END PHASE 15C LOCK */")
    assert panel_start != -1
    assert panel_end != -1

    panel = text[panel_start:panel_end]

    for phrase in [
        "does not mutate reputation",
        "publish rankings",
        "create bookings",
        "move money",
        "create payment",
        "create escrow",
        "send external messages",
        "execute workflows",
    ]:
        assert phrase in panel

    forbidden = [
        "mutateReputation(",
        "publishRanking(",
        "acceptExternalScore(",
        "createBooking(",
        "capturePayment(",
        "releaseEscrow(",
        "sendExternalMessage(",
    ]

    for item in forbidden:
        assert item not in panel
