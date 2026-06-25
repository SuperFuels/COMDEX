from pathlib import Path

APP_PATH = Path("desktop/mac/src/app.js")
TEXT = APP_PATH.read_text(encoding="utf-8")


def read_app():
    return APP_PATH.read_text(encoding="utf-8")


def phase25g_block():
    text = read_app()
    start = text.index("/* PHASE 25G LOCK: Boardroom Cross-Department Review */")
    end = text.index("function renderFinanceWorkspaceSurface", start)
    return text[start:end]


def test_phase25g_lock_marker_exists():
    assert "/* PHASE 25G LOCK: Boardroom Cross-Department Review */" in read_app()


def test_phase25g_helpers_exist():
    block = phase25g_block()

    assert "function classifyAionDepartmentCrossReviewState" in block
    assert "function buildAionBoardroomCrossDepartmentReview" in block
    assert "function renderBoardroomCrossDepartmentReviewPanel" in block
    assert "function renderBoardroomSpatialCrossDepartmentReviewPanel" in block


def test_phase25g_review_outputs_required_fields():
    block = phase25g_block()

    assert "complete_departments" in block
    assert "partial_departments" in block
    assert "missing_departments" in block
    assert "conflicts" in block
    assert "opportunities" in block
    assert "recommended_next_questions" in block
    assert "confidence" in block


def test_phase25g_detects_cross_department_conflicts():
    block = phase25g_block()

    assert "marketing_without_sales_followup" in block
    assert "marketing_without_finance_limits" in block
    assert "marketing_without_operations_capacity" in block
    assert "sales_without_margin_model" in block
    assert "support_without_operations_feedback" in block


def test_phase25g_uses_department_intelligence_and_assessment_feed():
    block = phase25g_block()

    assert "getAionDepartmentIntelligence()" in block
    assert "buildAionDepartmentAssessmentFeed" in block
    assert "getAionDepartmentResultEvidenceStatus" in block
    assert "getAionCoreDepartmentKeys().map" in block


def test_phase25g_boardroom_flat_mount_exists():
    text = read_app()

    assert 'data-aion-phase25g-boardroom-cross-department-review="true"' in text
    assert "renderBoardroomCrossDepartmentReviewPanel()" in text
    assert "renderBoardroomAssessmentFeedPanel()" in text


def test_phase25g_spatial_mount_exists():
    text = read_app()

    assert 'data-aion-phase25g-spatial-cross-department-review="true"' in text
    assert "renderBoardroomSpatialCrossDepartmentReviewPanel()" in text
    assert "renderBoardroomSpatialAssessmentFeedPanel()" in text


def test_phase25g_exports_debug_helpers():
    block = phase25g_block()

    assert "window.classifyAionDepartmentCrossReviewState" in block
    assert "window.buildAionBoardroomCrossDepartmentReview" in block
    assert "window.renderBoardroomCrossDepartmentReviewPanel" in block


def test_phase25g_no_live_external_execution_added():
    block = phase25g_block().lower()

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
