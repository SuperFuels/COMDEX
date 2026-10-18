from pathlib import Path


DOC = Path("docs/rfc/aion_phase21f_lrm_boardroom_projection_panel_lock.tex")


def test_phase21f_doc_exists():
    assert DOC.exists()


def test_phase21f_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 21F",
        "Read-only LRM Boardroom Projection Panel",
        "renderAionLrmBoardroomProjectionPanel",
        "renderBoardroomDashboardView",
        "getAionPilotFrontendInteractionState",
        "lrm_pilot_context_payload",
        "boardroom_projection",
        "lrm_context_payload_hash",
        "lrm_next_review_state",
        "lrm_loop_hash",
        "proof anchors",
        "read-only",
        "projection-only",
        "no duplicate Pilot",
        "no Boardroom replacement",
        "preview-only",
        "human review",
        "no booking",
        "no payment",
        "no escrow",
        "no external message",
        "no live chain",
        "no workflow execution",
        "no private chain-of-thought",
        "Tessaris AI",
        "Kevin Robinson",
    ]:
        assert term in text
