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


def central_plan_block():
    text = read_app()
    start = text.index("function buildAionPilotUniversalPlan")
    end = text.index("function buildAionPilotWorkPackage", start)
    return text[start:end]


def central_mission_block():
    text = read_app()
    start = text.index("function createAionPilotFrontendDraftMission")
    end = text.index("function renderAionPilotFrontendStreamEvents", start)
    return text[start:end]


def central_workspace_block():
    text = read_app()
    start = text.index("function renderAionWorkspaceSurface")
    end = text.index("function renderLiveAgentsWorkspaceBody", start)
    return text[start:end]


def test_phase25h_lock_marker_is_in_central_pilot_plan_area():
    text = read_app()
    h_index = text.index("/* PHASE 25H LOCK: Central AION Assessment Hook */")
    plan_index = text.index("function buildAionPilotUniversalPlan")
    finance_index = text.index("function renderFinanceWorkspaceSurface")

    assert h_index < plan_index
    assert plan_index < finance_index


def test_phase25h_helpers_exist():
    block = phase25h_block()

    assert "function buildAionCentralAssessmentInputBundle" in block
    assert "function buildAionCentralBusinessAssessment" in block
    assert "function buildAionCentralApprovalRequiredActionPlan" in block
    assert "function buildAionCentralPilotExecutionQueueProposal" in block
    assert "function buildAionCentralAssessmentHook" in block
    assert "function renderAionCentralAssessmentHookPanel" in block


def test_phase25h_reads_existing_business_boardroom_department_sources():
    block = phase25h_block()

    assert "getApprovedSmallBusinessFoundationContext" in block
    assert "getAionDepartmentIntelligence" in block
    assert "getBoardroomSnapshot" in block
    assert "getBoardroomRuntime" in block
    assert "buildAionDepartmentAssessmentFeed" in block
    assert "buildAionBoardroomCrossDepartmentReview" in block


def test_phase25h_plan_carries_assessment_hook_outputs():
    block = central_plan_block()

    assert "central_aion_assessment_hook" in block
    assert "central_business_assessment" in block
    assert "central_action_plan" in block
    assert "central_execution_queue_proposal" in block
    assert "buildAionCentralAssessmentHook(requestText)" in block


def test_phase25h_mission_visible_stream_mentions_assessment_hook():
    block = central_mission_block()

    assert 'type: "central_aion_assessment_hook"' in block
    assert "AION assessment hook prepared" in block
    assert "proposal_only" in block


def test_phase25h_central_workspace_keeps_assessment_out_of_default_stream_chrome():
    block = central_workspace_block()

    assert "renderAionCentralAssessmentHookPanel" not in block
    assert "renderAionPilotCockpitPanel" in block


def test_phase25h_exports_debug_helpers():
    block = phase25h_block()

    assert "window.buildAionCentralAssessmentInputBundle" in block
    assert "window.buildAionCentralBusinessAssessment" in block
    assert "window.buildAionCentralApprovalRequiredActionPlan" in block
    assert "window.buildAionCentralPilotExecutionQueueProposal" in block
    assert "window.buildAionCentralAssessmentHook" in block


def test_phase25h_no_live_external_execution_added():
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
