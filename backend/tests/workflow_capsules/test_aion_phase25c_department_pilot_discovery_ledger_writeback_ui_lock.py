from pathlib import Path

APP_PATH = Path("desktop/mac/src/app.js")
TEXT = APP_PATH.read_text(encoding="utf-8")


def phase25c_block():
    start = TEXT.index("/* PHASE 25C LOCK: Department Pilot Discovery Ledger Writeback */")
    end = TEXT.index("/* END PHASE 25C LOCK */", start)
    return TEXT[start:end]


def test_phase25c_lock_markers_exist():
    block = phase25c_block()

    assert "PHASE 25C LOCK: Department Pilot Discovery Ledger Writeback" in block
    assert "END PHASE 25C LOCK" not in block


def test_phase25c_department_discovery_templates_exist():
    block = phase25c_block()

    assert "AION_DEPARTMENT_PILOT_DISCOVERY_TEMPLATES" in block
    for key in ["marketing", "sales", "finance", "operations", "support"]:
        assert f"{key}:" in block

    assert "social_accounts" in block
    assert "lead_sources" in block
    assert "pricing" in block
    assert "core_workflows" in block
    assert "common_enquiries" in block


def test_phase25c_discovery_writes_to_department_intelligence():
    block = phase25c_block()

    assert "function saveAionDepartmentPilotDiscovery" in block
    assert "collectAionDepartmentPilotDiscoveryFromForm" in block
    assert "updateAionDepartmentIntelligence(key, nextEntry)" in block
    assert "discovery: nextDiscovery" in block
    assert "boardroom_summary" in block
    assert "last_updated" in block


def test_phase25c_plan_and_queue_writeback_exist():
    block = phase25c_block()

    assert "function buildAionDepartmentPilotPlanDraft" in block
    assert "function buildAionDepartmentPilotSafeTaskQueue" in block
    assert "plan," in block
    assert "tasks," in block
    assert 'status: "plan_ready"' in block
    assert 'status: "queue_ready"' in block


def test_phase25c_department_surfaces_render_discovery_plan_queue_and_sync():
    block = phase25c_block()

    assert "renderAionDepartmentPilotDiscoveryPanel" in block
    assert "renderAionDepartmentPilotPlanPanel" in block
    assert "renderAionDepartmentPilotSafeQueuePanel" in block
    assert "renderAionDepartmentPilotLedgerSyncPanel" in block
    assert 'data-aion-phase25c-department-pilot-discovery="' in block
    assert 'data-aion-phase25c-department-pilot-ledger-writeback="' in block


def test_phase25c_buttons_are_event_bound():
    block = phase25c_block()

    assert "data-aion-phase25c-save-discovery" in block
    assert "data-aion-phase25c-build-plan" in block
    assert "data-aion-phase25c-build-queue" in block
    assert "window.__aionPhase25CDepartmentPilotDiscoveryHandlersInstalled" in block


def test_phase25c_generic_department_workspace_mounts_panel():
    start = TEXT.index("function renderGenericDepartmentWorkspaceSurface")
    end = TEXT.index("function renderFinanceWorkspaceSurface", start)
    block = TEXT[start:end]

    assert "${renderAionDepartmentPilotPhase25CPanel(departmentKey)}" in block


def test_phase25c_marketing_workspace_mounts_panel():
    start = TEXT.index("function renderPilotMarketingWorkspaceSurface")
    end = TEXT.index("function renderMarketingManualWorkspaceSurface", start)
    block = TEXT[start:end]

    assert 'data-aion-marketing-automation-studio="true"' in block
    assert "getAionPilotMarketingWorkspaceArtifacts()" in block
    assert 'renderAionDepartmentPilotPhase25CPanel("marketing")' not in block


def test_phase25c_exports_safe_debug_helpers():
    block = phase25c_block()

    assert "window.getAionDepartmentPilotDiscoveryTemplate" in block
    assert "window.saveAionDepartmentPilotDiscovery" in block
    assert "window.buildAionDepartmentPilotPlanDraft" in block
    assert "window.buildAionDepartmentPilotSafeTaskQueue" in block


def test_phase25c_no_live_external_execution_added():
    block = phase25c_block().lower()

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
