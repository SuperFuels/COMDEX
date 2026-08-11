from pathlib import Path

APP_PATH = Path("desktop/mac/src/app.js")
TEXT = APP_PATH.read_text(encoding="utf-8")


def read_app():
    return APP_PATH.read_text(encoding="utf-8")


def phase25f_block():
    text = read_app()
    start = text.index("/* PHASE 25F LOCK: Department-specific Pilot Expansion */")
    end = text.index("function renderFinanceWorkspaceSurface", start)
    return text[start:end]


def test_phase25f_lock_marker_exists():
    assert "/* PHASE 25F LOCK: Department-specific Pilot Expansion */" in read_app()


def test_phase25f_specialist_playbooks_exist_for_all_departments():
    block = phase25f_block()

    assert "AION_DEPARTMENT_PILOT_SPECIALIST_PLAYBOOKS" in block
    for key in ["marketing", "sales", "finance", "operations", "support"]:
        assert f"{key}:" in block

    assert "campaign_draft" in block
    assert "pipeline_map" in block
    assert "pricing_review" in block
    assert "workflow_map" in block
    assert "support_map" in block


def test_phase25f_specialist_builder_helpers_exist():
    block = phase25f_block()

    assert "function getAionDepartmentPilotSpecialistPlaybook" in block
    assert "function buildAionDepartmentPilotSpecialistDraft" in block
    assert "function buildAionDepartmentPilotSpecialistSafeQueue" in block
    assert "function renderAionDepartmentPilotPhase25FPanel" in block


def test_phase25f_writes_specialist_plan_and_queue_to_ledger():
    block = phase25f_block()

    assert "specialist_plan" in block
    assert 'status: "specialist_plan_ready"' in block
    assert 'status: "specialist_queue_ready"' in block
    assert "updateAionDepartmentIntelligence" in block
    assert "tasks:" in block
    assert "boardroom_summary" in block


def test_phase25f_renders_specialist_panel_and_buttons():
    text = read_app()

    assert 'data-aion-phase25f-department-specialist-pilot="true"' in text
    assert "data-aion-phase25f-build-specialist-plan" in text
    assert "data-aion-phase25f-build-specialist-queue" in text


def test_phase25f_mounts_in_generic_department_workspace():
    text = read_app()
    start = text.index("function renderGenericDepartmentWorkspaceSurface")
    end = text.index("function renderFinanceWorkspaceSurface", start)
    block = text[start:end]

    assert "renderAionDepartmentPilotPhase25EPanel(departmentKey)" in block
    assert "renderAionDepartmentPilotPhase25FPanel(departmentKey)" in block


def test_phase25f_mounts_in_marketing_workspace():
    text = read_app()
    start = text.index("function renderPilotMarketingWorkspaceSurface")
    end = text.index("function renderMarketingManualWorkspaceSurface", start)
    block = text[start:end]

    assert 'data-aion-marketing-automation-studio="true"' in block
    assert "renderMarketingStreamSurface({ embedded: true })" in block
    assert 'renderAionDepartmentPilotPhase25EPanel("marketing")' not in block
    assert 'renderAionDepartmentPilotPhase25FPanel("marketing")' not in block


def test_phase25f_exports_debug_helpers():
    block = phase25f_block()

    assert "window.getAionDepartmentPilotSpecialistPlaybook" in block
    assert "window.buildAionDepartmentPilotSpecialistDraft" in block
    assert "window.buildAionDepartmentPilotSpecialistSafeQueue" in block


def test_phase25f_no_live_external_execution_added():
    block = phase25f_block().lower()

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
