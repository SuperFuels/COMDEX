from pathlib import Path

APP_PATH = Path("desktop/mac/src/app.js")
TEXT = APP_PATH.read_text(encoding="utf-8")


def read_app():
    return APP_PATH.read_text(encoding="utf-8")


def phase25e_block():
    text = read_app()
    start = text.index("/* PHASE 25E LOCK: Department Results Evidence Boardroom Assessment Feed */")
    end = text.index("function renderFinanceWorkspaceSurface", start)
    return text[start:end]


def test_phase25e_lock_marker_exists():
    assert "/* PHASE 25E LOCK: Department Results Evidence Boardroom Assessment Feed */" in read_app()


def test_phase25e_helpers_exist():
    block = phase25e_block()

    assert "function getAionDepartmentResultEvidenceStatus" in block
    assert "function buildAionDepartmentAssessmentFeed" in block
    assert "function renderBoardroomAssessmentFeedPanel" in block
    assert "function renderBoardroomSpatialAssessmentFeedPanel" in block
    assert "function renderAionDepartmentPilotPhase25EPanel" in block


def test_phase25e_safe_task_completion_writes_results_evidence_receipts():
    text = read_app()

    assert "latest_safe_preview" in text
    assert "safe_preview_history" in text
    assert "evidenceRecord" in text
    assert "resultRecord" in text
    assert "receipts:" in text
    assert "results:" in text
    assert "evidence:" in text


def test_phase25e_boardroom_flat_mount_exists():
    text = read_app()

    assert 'data-aion-phase25e-boardroom-assessment-feed="true"' in text
    assert "renderBoardroomAssessmentFeedPanel()" in text
    assert "renderBoardroomDepartmentIntelligencePanel()" in text


def test_phase25e_spatial_mount_exists():
    text = read_app()

    assert 'data-aion-phase25e-spatial-assessment-feed="true"' in text
    assert "renderBoardroomSpatialAssessmentFeedPanel()" in text


def test_phase25e_department_workspace_mount_exists():
    text = read_app()

    assert 'data-aion-phase25e-department-results-evidence="true"' in text
    assert "renderAionDepartmentPilotPhase25EPanel(departmentKey)" in text
    assert 'data-aion-marketing-automation-studio="true"' in text
    assert "getAionPilotMarketingWorkspaceArtifacts()" in text
    assert 'renderAionDepartmentPilotPhase25EPanel("marketing")' not in TEXT[TEXT.index("function renderPilotMarketingWorkspaceSurface"):TEXT.index("function renderMarketingManualWorkspaceSurface", TEXT.index("function renderPilotMarketingWorkspaceSurface"))]


def test_phase25e_exports_debug_helpers():
    block = phase25e_block()

    assert "window.getAionDepartmentResultEvidenceStatus" in block
    assert "window.buildAionDepartmentAssessmentFeed" in block
    assert "window.renderBoardroomAssessmentFeedPanel" in block


def test_phase25e_no_live_external_execution_added():
    block = phase25e_block().lower()

    forbidden = [
        "sendemail(",
        "send_email(",
        "publishad(",
        "chargecard(",
        "createbooking(",
        "live_send_enabled: true",
        "external_writes_enabled",
    ]

    for token in forbidden:
        assert token not in block
