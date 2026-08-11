from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def phase25b_block() -> str:
    text = read_app()
    start = text.index("/* PHASE 25B LOCK: Department-scoped Live Agent Pilot surfaces */")
    end = text.index("/* END PHASE 25B LOCK */", start)
    return text[start:end]


def test_phase25b_department_scoped_pilot_contract_exists():
    block = phase25b_block()

    assert "AION_DEPARTMENT_PILOT_PROFILES" in block
    assert "function renderAionDepartmentScopedPilotSurface" in block
    assert "function applyAionDepartmentPilotAction" in block
    assert "data-aion-phase25b-department-scoped-pilot=\"true\"" in block


def test_phase25b_core_departments_have_profiles():
    block = phase25b_block()

    for key in ["marketing", "sales", "finance", "operations", "support"]:
        assert f"{key}:" in block


def test_phase25b_department_pilots_write_to_department_intelligence_ledger():
    block = phase25b_block()

    assert "updateAionDepartmentIntelligence(key" in block
    assert "boardroom_summary" in block
    assert "last_updated" in block
    assert "source: \"phase25b_department_scoped_pilot\"" in block


def test_phase25b_live_agent_workspaces_route_to_unified_department_shells():
    text = read_app()

    assert "AION_UNIFIED_DEPARTMENT_SHELLS" in text
    assert "renderDepartmentCompactDirectorCard" in text
    assert "return renderFinanceWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);" in text
    assert "return renderSalesWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);" in text
    assert "return renderOperationsWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);" in text
    assert "return renderSupportWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);" in text
    assert "return renderHRWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);" in text
    assert "return renderPilotMarketingWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);" in text


def test_phase25b_central_pilot_still_exists():
    text = read_app()

    assert "function renderAionWorkspaceSurface" in text
    assert "renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())" in text
    assert "data-aion-live-agents-aion-pilot-workspace" in text


def test_phase25b_persistent_pilot_uses_persistent_terminal_input():
    text = read_app()

    assert 'document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]")' in text
    assert "persistentInput?.value" in text


def test_phase25b_department_pilot_mission_updates_ledger():
    text = read_app()

    assert "central_pilot_department_scope" in text
    assert "pilotState.department_scope" in text
    assert "updateAionDepartmentIntelligence(pilotState.department_scope" in text


def test_phase25b_no_live_external_execution_added():
    block = phase25b_block().lower()

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
