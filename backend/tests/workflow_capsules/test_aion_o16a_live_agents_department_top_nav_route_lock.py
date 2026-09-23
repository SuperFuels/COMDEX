from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop" / "mac" / "src" / "app.js"

def test_o16a_live_agents_department_route_lock_installed():
    text = APP.read_text(encoding="utf-8")
    assert "O16A LIVE AGENTS DEPARTMENT TOP NAV ROUTE LOCK" in text
    assert "window.__setAionO16ALiveAgentsDepartment" in text
    assert "window.aionOpenLiveAgentsDepartmentO16A" in text
    assert 'window.setAionSidebarActiveTabHardV1("live_agents")' in text
    assert 'window.__aionForcedMainTabV2 = "live_agents"' in text
    assert "window.__debugAionO16ALiveAgentsDepartmentRoute" in text

def test_o16a_routes_all_department_buttons():
    text = APP.read_text(encoding="utf-8")
    block = text[text.find("BEGIN AION O16A"):text.find("END AION O16A")]
    for key in ["marketing", "sales", "finance", "operations", "support", "hr", "pilot", "builder"]:
        assert f'"{key}"' in block

def test_o16a_click_handler_uses_live_agents_department_attrs():
    text = APP.read_text(encoding="utf-8")
    block = text[text.find("BEGIN AION O16A"):text.find("END AION O16A")]
    assert "data-aion-live-agents-department" in block
    assert "data-aion-o14p-live-agents-department" in block
    assert "event.stopImmediatePropagation" in block
    assert 'setActiveTab("live_agents")' in block
    assert "requestRender" in block

def test_o16a_selection_updates_renderer_authority_and_runtime_state():
    text = APP.read_text(encoding="utf-8")
    block = text[text.find("BEGIN AION O16A"):text.find("END AION O16A")]
    assert "window.__aionO16ASelectedLiveAgentsDepartment = departmentKey" in block
    assert "window.__aionLiveAgentsFocusDepartment = departmentKey" in block
    assert "state.selectedLiveAgentDepartment = departmentKey" in block
    assert "state.liveAgentsSelectedDepartment = departmentKey" in block
    assert 'localStorage?.setItem?.("aion.liveAgents.selectedDepartment", departmentKey)' in block
    assert 'localStorage?.setItem?.("aion.liveAgents.focusDepartment.v1", departmentKey)' in block
