from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def text():
    return APP.read_text()


def test_phase23d_approved_work_package_keeps_continue_button_visible():
    src = text()

    start = src.index("function renderAionPilotWorkPackageCard")
    end = src.index("function normaliseAionPilotPreviewText", start)
    block = src[start:end]

    assert "✓ Approved" in block
    assert "data-aion-pilot-continue-safe-work" in block
    assert "Continue safe work" in block


def test_phase23d_approve_no_longer_auto_executes_safe_work():
    src = text()

    start = src.index("function approveAionPilotMissionContract")
    end = src.index("function reviseAionPilotMissionContract", start)
    block = src[start:end]

    assert "approved_for_safe_work" in block
    assert "runAionPilotSafeWorkPreview();" not in block


def test_phase23d_continue_button_runs_backend_mission_preview_runner():
    src = text()

    assert "data-aion-pilot-continue-safe-work" in src

    start = src.index('target.closest("[data-aion-pilot-continue-safe-work]")')
    block = src[start:start + 400]

    assert "runAionPilotSafeWorkPreview();" in block
    assert "return;" in block


def test_phase23d_runner_uses_phase23c_backend_bridge():
    src = text()

    start = src.index("async function runAionPilotSafeWorkPreview")
    end = src.index("/* END PHASE 21T LOCK */", start)
    block = src[start:end]

    assert "fetchAionPilotMissionPreviewIntoPilotState" in block
    assert "executeAndAppendAionPilotMissionMapStepOutput" in block
    assert "business_context_mission_map_ready" in block
