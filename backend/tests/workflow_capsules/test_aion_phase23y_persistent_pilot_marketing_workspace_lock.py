from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js").read_text()


def _live_agents_workspace_body() -> str:
    body_start = APP_JS.index("function renderLiveAgentsWorkspaceBody")
    body_end = APP_JS.index("function renderLiveAgentRunRow", body_start)
    return APP_JS[body_start:body_end]


def test_phase23y_live_agents_mounts_persistent_pilot_terminal():
    assert "function renderLiveAgentsPersistentPilotTerminal" in APP_JS
    assert "data-aion-phase23y-persistent-pilot-terminal" in APP_JS
    assert "${renderLiveAgentsPersistentPilotTerminal()}" in APP_JS
    assert "data-aion-phase23y-persistent-pilot-terminal" in APP_JS


def test_phase23y_marketing_workspace_has_manual_and_pilot_tabs():
    assert "function renderLiveAgentsMarketingWorkspaceTabs" in APP_JS
    assert 'data-aion-marketing-workspace-mode="manual"' in APP_JS
    assert 'data-aion-marketing-workspace-mode="pilot"' in APP_JS
    assert "Manual" in APP_JS
    assert "Pilot Marketing" in APP_JS


def test_phase23y_marketing_branch_uses_manual_or_pilot_workspace_not_generic_stream():
    body = _live_agents_workspace_body()

    branch_start = body.index('if (departmentKey === "marketing")')
    finance_start = body.index('if (departmentKey === "finance")', branch_start)
    branch = body[branch_start:finance_start]

    assert "getLiveAgentsMarketingWorkspaceMode()" in branch
    assert "return renderMarketingManualWorkspaceSurface();" in branch
    assert "return renderPilotMarketingWorkspaceSurface(selectedRuns, selectedAgentCard);" in branch


def test_phase23y_pilot_marketing_workspace_surfaces_pilot_outputs():
    assert "function getAionPilotMarketingWorkspaceArtifacts" in APP_JS
    assert "data-aion-phase23y-pilot-marketing-workspace" in APP_JS
    assert "data-aion-phase23y-pilot-marketing-artifact-card" in APP_JS
    assert "tool_execution_queue" in APP_JS
    assert "step_outputs" in APP_JS


def test_phase23y_manual_workspace_preserves_existing_manual_generator_link():
    assert "function renderMarketingManualWorkspaceSurface" in APP_JS
    assert "data-aion-open-manual-marketing-stream" in APP_JS
    assert 'state.activeTab = "marketing_stream";' in APP_JS
    assert "Open manual generator" in APP_JS


def test_phase23y_handlers_are_direct_and_stop_propagation():
    assert "__aionPhase23YMarketingWorkspaceHandlersInstalled" in APP_JS
    assert "event.stopPropagation();" in APP_JS
    assert "state.liveAgentsMarketingWorkspaceMode" in APP_JS


def test_phase23y_pilot_terminal_is_sticky_footer_after_workspace_body():
    surface_start = APP_JS.index("function renderLiveAgentsSurface")
    surface_end = APP_JS.index("function findSelectedLiveRun", surface_start)
    surface = APP_JS[surface_start:surface_end]

    body_index = surface.index("${renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard)}")
    terminal_index = surface.index("${renderLiveAgentsPersistentPilotTerminal()}")

    assert body_index < terminal_index
    assert "position:sticky;" in APP_JS
    assert "bottom:0;" in APP_JS
    assert "data-aion-phase23y-persistent-pilot-start" in APP_JS
    assert "Tell Pilot what to do..." in APP_JS


def test_phase23y_persistent_pilot_terminal_can_start_task():
    assert "data-aion-phase23y-persistent-pilot-start" in APP_JS
    assert "createAionPilotFrontendDraftMission();" in APP_JS
    assert "pilotState.last_request = value;" in APP_JS


def test_phase23y_persistent_pilot_terminal_is_compact_not_big_header_panel():
    terminal_start = APP_JS.index("function renderLiveAgentsPersistentPilotTerminal")
    terminal_end = APP_JS.index("if (!window.__aionPhase23YMarketingWorkspaceHandlersInstalled)", terminal_start)
    terminal = APP_JS[terminal_start:terminal_end]

    assert "Persistent Pilot Terminal" not in terminal
    assert "AION works from here; departments are visible workspaces." not in terminal
    assert "Preview only" not in terminal
    assert "No live side effects" not in terminal
    assert "min-height:44px" in terminal
    assert "padding:8px 12px 10px" in terminal
