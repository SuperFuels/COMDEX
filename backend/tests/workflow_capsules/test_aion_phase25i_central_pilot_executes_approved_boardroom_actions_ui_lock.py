from pathlib import Path

APP_PATH = Path("desktop/mac/src/app.js")
TEXT = APP_PATH.read_text(encoding="utf-8")


def read_app():
    return APP_PATH.read_text(encoding="utf-8")


def phase25h_block():
    text = read_app()
    start = text.index("/* PHASE 25H LOCK: Central AION Assessment Hook */")
    end = text.index("function buildAionPilotUniversalPlan", start)
    return text[start:end]


def central_workspace_block():
    text = read_app()
    start = text.index("function renderAionWorkspaceSurface")
    end = text.index("function renderLiveAgentsWorkspaceBody", start)
    return text[start:end]


def test_phase25i_updates_existing_phase25h_block_not_department_append():
    text = read_app()
    h_start = text.index("/* PHASE 25H LOCK: Central AION Assessment Hook */")
    h_end = text.index("function buildAionPilotUniversalPlan", h_start)
    finance = text.index("function renderFinanceWorkspaceSurface")

    assert h_start < h_end < finance
    assert "AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY" in text[h_start:h_end]


def test_phase25i_storage_keys_exist():
    block = phase25h_block()

    assert 'const AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY = "aion.centralApprovedBoardroomActions";' in block
    assert 'const AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY = "aion.centralPilotQueue";' in block


def test_phase25i_approval_and_queue_helpers_exist():
    block = phase25h_block()

    assert "function getAionCentralApprovedBoardroomActions" in block
    assert "function saveAionCentralApprovedBoardroomActions" in block
    assert "function getAionCentralPilotQueue" in block
    assert "function saveAionCentralPilotQueue" in block
    assert "function approveAionCentralBoardroomAction" in block
    assert "function buildAionCentralApprovedPilotQueue" in block
    assert "function getAionCentralPilotNextApprovedTask" in block
    assert "function runAionCentralPilotApprovedTask" in block


def test_phase25i_safe_execution_writes_back_to_department_ledger():
    block = phase25h_block()

    assert "updateAionDepartmentIntelligence" in block
    assert "latest_central_preview" in block
    assert "central_preview_history" in block
    assert "central_boardroom_action_result" in block
    assert "central_safe_internal_preview" in block
    assert "central_action_preview_complete" in block


def test_phase25i_renders_approved_boardroom_actions_panel():
    block = phase25h_block()

    assert "function renderAionCentralApprovedBoardroomActionsPanel" in block
    assert 'data-aion-phase25i-central-approved-boardroom-actions="true"' in block
    assert "data-aion-phase25i-approve-boardroom-action" in block
    assert "data-aion-phase25i-build-central-queue" in block
    assert "data-aion-phase25i-run-central-task" in block


def test_phase25i_keeps_boardroom_action_panels_out_of_default_conversation_stream():
    block = central_workspace_block()

    assert "renderAionCentralAssessmentHookPanel" not in block
    assert "renderAionCentralApprovedBoardroomActionsPanel" not in block
    assert "renderAionPilotCockpitPanel" in block


def test_phase25i_exports_debug_helpers():
    block = phase25h_block()

    assert "window.approveAionCentralBoardroomAction" in block
    assert "window.buildAionCentralApprovedPilotQueue" in block
    assert "window.runAionCentralPilotApprovedTask" in block
    assert "window.getAionCentralPilotQueue" in block


def test_phase25i_no_live_external_execution_added():
    block = phase25h_block().lower()

    forbidden = [
        "sendemail(",
        "send_email(",
        "publishad(",
        "chargecard(",
        "createbooking(",
        "live_send_enabled: true",
        "external_writes_enabled",
        "fetch(",
    ]

    for token in forbidden:
        assert token not in block
