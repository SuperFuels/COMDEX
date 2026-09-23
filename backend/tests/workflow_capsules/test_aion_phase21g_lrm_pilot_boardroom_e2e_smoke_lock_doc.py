from pathlib import Path


DOC = Path("docs/rfc/aion_phase21g_lrm_pilot_boardroom_e2e_smoke_lock.tex")
SCRIPT = Path("scripts/run_aion_lrm_phase21g_smoke.sh")


def test_phase21g_doc_exists():
    assert DOC.exists()


def test_phase21g_script_exists():
    assert SCRIPT.exists()


def test_phase21g_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 21G",
        "End-to-End Local Smoke Test",
        "local API endpoint",
        "frontend fetch bridge",
        "existing Pilot state",
        "Pilot readonly LRM context card",
        "Boardroom readonly LRM projection panel",
        "/api/local-node/aion/lrm/pilot-context-preview",
        "getAionLrmPilotContextPreviewUrl",
        "fetchAionLrmPilotContextPreviewIntoPilotState",
        "applyAionLrmPilotContextPreviewPayload",
        "renderAionLrmPilotContextReadonlyCard",
        "renderAionLrmBoardroomProjectionPanel",
        "renderAionPilotSimpleTaskStream",
        "renderBoardroomDashboardView",
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


def test_phase21g_script_runs_targeted_tests():
    text = SCRIPT.read_text()

    assert "test_aion_phase21g_lrm_pilot_boardroom_e2e_smoke_lock.py" in text
    assert "test_aion_phase21g_lrm_pilot_boardroom_e2e_smoke_lock_doc.py" in text
    assert "compileall backend/modules/aion_lrm backend/services/aion_mission_mode backend/api" in text
