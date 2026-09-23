from pathlib import Path

APP_PATH = Path("desktop/mac/src/app.js")
TEXT = APP_PATH.read_text(encoding="utf-8")


def read_app():
    return APP_PATH.read_text(encoding="utf-8")


def scoped_surface_block():
    text = read_app()
    start = text.index("function renderAionDepartmentScopedPilotSurface")
    end = text.index("function applyAionDepartmentPilotAction", start)
    return text[start:end]


def boardroom_dashboard_block():
    text = read_app()
    start = text.index("function renderBoardroomDashboardView")
    end = text.index("function openDepartmentWorkspaceFromBoardroom", start)
    return text[start:end]


def boardroom_spatial_block():
    text = read_app()
    start = text.index("function renderBoardroomSpatialView")
    end = text.index("function renderBoardroomSurface", start)
    return text[start:end]


def test_phase25j_department_pilot_surface_is_guided_workflow():
    block = scoped_surface_block()

    assert 'data-aion-phase25j-department-pilot-guided-workflow="true"' in block
    assert "Next step:" in block
    assert "How this department Pilot works" in block
    assert "Where to see it working" in block


def test_phase25j_old_confusing_buttons_removed_from_scoped_surface():
    block = scoped_surface_block()

    assert 'data-aion-department-pilot-action="seed_discovery"' not in block
    assert 'data-aion-department-pilot-action="build_plan"' not in block
    assert 'data-aion-department-pilot-action="stage_safe_queue"' not in block
    assert "Run Finance discovery" not in block
    assert "Build department plan preview" not in block
    assert "Stage safe execution queue" not in block


def test_phase25j_real_workflow_panels_mount_inside_scoped_surface():
    block = scoped_surface_block()

    assert "renderAionDepartmentPilotPhase25CPanel(key)" in block
    assert "renderAionDepartmentPilotPhase25DPanel(key)" in block
    assert "renderAionDepartmentPilotPhase25EPanel(key)" in block
    assert "renderAionDepartmentPilotPhase25FPanel(key)" in block


def test_phase25j_department_pilot_explains_ledger_and_safety():
    block = scoped_surface_block()

    assert "aion.departmentIntelligence." in block
    assert "does not send, publish, spend, book, invoice, deploy or mutate external systems" in block


def test_phase25j_boardroom_flat_visibly_mounts_intelligence_near_top():
    block = boardroom_dashboard_block()

    assert 'data-aion-phase25j-boardroom-visible-intelligence="true"' in block
    assert "renderBoardroomDepartmentIntelligencePanel()" in block
    assert "renderBoardroomAssessmentFeedPanel()" in block
    assert "renderBoardroomCrossDepartmentReviewPanel()" in block
    assert "renderAionProviderCouncilPanel()" not in block
    assert "renderBoardroomPulseSummaryStrip(snapshot)" not in block
    assert block.index("renderBoardroomDepartmentIntelligencePanel") < block.index("renderBoardroomAssessmentFeedPanel")
    assert block.index("renderBoardroomCrossDepartmentReviewPanel") < block.index("renderBoardroomOperatorPresence")


def test_phase25j_spatial_boardroom_visibly_mounts_intelligence():
    block = boardroom_spatial_block()

    assert 'data-aion-phase25j-spatial-visible-intelligence="true"' in block
    assert "renderBoardroomSpatialDepartmentIntelligencePanel()" in block
    assert "renderBoardroomSpatialAssessmentFeedPanel()" in block
    assert "renderBoardroomSpatialCrossDepartmentReviewPanel()" in block
    assert block.index("renderBoardroomSpatialDepartmentIntelligencePanel") < block.index("renderBoardroomDepartments(departments)")


def test_phase25j_no_live_external_execution_added():
    block = scoped_surface_block().lower() + boardroom_dashboard_block().lower() + boardroom_spatial_block().lower()

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
