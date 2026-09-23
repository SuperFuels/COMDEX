from pathlib import Path

APP_PATH = Path("desktop/mac/src/app.js")
TEXT = APP_PATH.read_text(encoding="utf-8")


def read_app():
    return APP_PATH.read_text(encoding="utf-8")


def phase25d_block():
    text = read_app()
    start = text.index("/* PHASE 25D LOCK: Department Plan Approval + Safe Queue Execution */")
    end = text.index("function renderFinanceWorkspaceSurface", start)
    return text[start:end]


def test_phase25d_lock_marker_exists():
    assert "/* PHASE 25D LOCK: Department Plan Approval + Safe Queue Execution */" in read_app()


def test_phase25d_helpers_exist():
    block = phase25d_block()

    assert "function getAionDepartmentPilotApprovalState" in block
    assert "function approveAionDepartmentPilotPlan" in block
    assert "function getAionDepartmentPilotApprovedTaskQueue" in block
    assert "function getAionDepartmentPilotNextSafeTask" in block
    assert "function runAionDepartmentPilotNextSafeTask" in block


def test_phase25d_uses_existing_discovery_plan_queue_builders():
    block = phase25d_block()

    assert "buildAionDepartmentPilotPlanDraft" in block
    assert "buildAionDepartmentPilotSafeTaskQueue" in block
    assert "updateAionDepartmentIntelligence" in block


def test_phase25d_writes_approval_and_safe_queue_status_to_ledger():
    block = phase25d_block()

    assert 'status: "plan_approved"' in block
    assert 'plan_approval_status: "approved"' in block
    assert "tasks: taskQueue" in block
    assert "runs:" in block
    assert "receipts:" in block
    assert 'status: "completed_preview"' in block


def test_phase25d_renders_department_safe_queue_panel():
    text = read_app()

    assert "function renderAionDepartmentPilotPhase25DPanel" in text
    assert 'data-aion-phase25d-department-pilot-safe-queue="true"' in text
    assert 'data-aion-phase25d-approve-plan' in text
    assert 'data-aion-phase25d-run-safe-task' in text


def test_phase25d_mounts_in_generic_department_workspace():
    text = read_app()
    start = text.index("function renderGenericDepartmentWorkspaceSurface")
    end = text.index("function renderFinanceWorkspaceSurface", start)
    block = text[start:end]

    assert "renderAionDepartmentPilotPhase25CPanel(departmentKey)" in block
    assert "renderAionDepartmentPilotPhase25DPanel(departmentKey)" in block


def test_phase25d_mounts_in_marketing_workspace():
    text = read_app()
    start = text.index("function renderPilotMarketingWorkspaceSurface")
    end = text.index("function renderMarketingManualWorkspaceSurface", start)
    block = text[start:end]

    assert 'data-aion-marketing-automation-studio="true"' in block
    assert "renderMarketingStreamSurface({ embedded: true })" in block
    assert 'renderAionDepartmentPilotPhase25CPanel("marketing")' not in block
    assert 'renderAionDepartmentPilotPhase25DPanel("marketing")' not in block


def test_phase25d_exports_debug_helpers():
    block = phase25d_block()

    assert "window.getAionDepartmentPilotApprovalState" in block
    assert "window.approveAionDepartmentPilotPlan" in block
    assert "window.runAionDepartmentPilotNextSafeTask" in block


def test_phase25d_no_live_external_execution_added():
    block = phase25d_block().lower()

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
