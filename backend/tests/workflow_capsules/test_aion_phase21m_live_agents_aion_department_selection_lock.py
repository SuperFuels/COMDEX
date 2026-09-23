from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
RUNTIME = Path("desktop/mac/src/live_agents_runtime.js").read_text(encoding="utf-8")


def test_phase21m_runtime_lock_marker_exists():
    assert "PHASE 21M LOCK: explicit Live Agents department selection wins" in RUNTIME


def test_phase21m_department_selection_prefers_explicit_state():
    start = RUNTIME.index("function getSelectedLiveDepartmentKey")
    end = RUNTIME.index("\n  function ", start + 1)
    block = RUNTIME[start:end]
    assert "selectedLiveDepartmentKey" in block
    assert "activeLiveDepartmentKey" in block
    assert "activeZone" in block
    assert "if (explicitDepartment)" in block
    assert "return explicitDepartment" in block


def test_phase21m_department_selection_does_not_force_agent_card_first():
    start = RUNTIME.index("function getSelectedLiveDepartmentKey")
    end = RUNTIME.index("\n  function ", start + 1)
    block = RUNTIME[start:end]
    explicit_idx = block.index("if (explicitDepartment)")
    agent_idx = block.index("const selectedAgentCard")
    assert explicit_idx < agent_idx


def test_phase21m_live_agents_body_routes_aion_to_aion_workspace():
    assert 'if (departmentKey === "aion")' in APP
    assert "return renderAionWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);" in APP


def test_phase21m_click_handler_calls_set_workspace_and_selection():
    start = APP.index('const liveDepartmentOpenButton = target.closest(".live-department-open-btn")')
    end = APP.index('const closeReplayButton = target.closest("#closeLiveAgentsReplayBtn")', start)
    block = APP[start:end]
    assert "setLiveAgentsWorkspace(departmentKey" in block
    assert "ensureLiveAgentSelection" in block
    assert "preferredDepartmentKey: departmentKey" in block
    assert "requestRender()" in block


def test_phase21m_pilot_still_mounted_in_live_agents_aion():
    assert "data-aion-phase21l-live-agents-aion-pilot-mount" in APP
    assert "Live Agents / Aion" in APP
    assert "renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())" in APP


def test_phase21m_top_level_aion_remains_pointer_only():
    start = APP.index("function renderAionChatSurface()")
    end = APP.index("function renderAionToolMiniCard", start)
    block = APP[start:end]
    assert "data-aion-pilot-chat-pointer" in block
    assert "Live Agents → Aion" in block
    assert "renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())" not in block


def test_phase21m_no_forbidden_live_pilot_buttons():
    for forbidden in [
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
    ]:
        assert forbidden not in APP
