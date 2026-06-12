from pathlib import Path


DOC = Path("docs/rfc/aion_phase21d_lrm_pilot_frontend_fetch_bridge_lock.tex")


def test_phase21d_doc_exists():
    assert DOC.exists()


def test_phase21d_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 21D",
        "Frontend Fetch Bridge",
        "AION-LRM",
        "Pilot Context Preview",
        "/api/local-node/aion/lrm/pilot-context-preview",
        "getAionLrmPilotContextPreviewUrl",
        "applyAionLrmPilotContextPreviewPayload",
        "fetchAionLrmPilotContextPreviewIntoPilotState",
        "getAionPilotFrontendInteractionState",
        "createAionPilotFrontendDraftMission",
        "existing Pilot state",
        "no duplicate Pilot",
        "no UI redesign",
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
