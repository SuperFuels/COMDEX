from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js").read_text()


def _live_agents_workspace_body() -> str:
    body_start = APP_JS.index("function renderLiveAgentsWorkspaceBody")
    body_end = APP_JS.index("function renderLiveAgentRunRow", body_start)
    return APP_JS[body_start:body_end]


def _live_agents_surface() -> str:
    surface_start = APP_JS.index("function renderLiveAgentsSurface")
    surface_end = APP_JS.index("function findSelectedLiveRun", surface_start)
    return APP_JS[surface_start:surface_end]


def _pilot_terminal() -> str:
    terminal_start = APP_JS.index("function renderLiveAgentsPersistentPilotTerminal")
    terminal_end = APP_JS.index("if (!window.__aionPhase23YMarketingWorkspaceHandlersInstalled)", terminal_start)
    return APP_JS[terminal_start:terminal_end]


def test_phase23y_legacy_fixed_bar_is_retained_but_not_mounted():
    assert "function renderLiveAgentsPersistentPilotTerminal" in APP_JS
    assert "data-aion-phase23y-persistent-pilot-terminal" in APP_JS
    assert "${renderLiveAgentsPersistentPilotTerminal()}" not in _live_agents_surface()
    assert "data-aion-phase23y-persistent-pilot-terminal-input" in APP_JS
    assert "data-aion-phase23y-persistent-pilot-start" in APP_JS


def test_phase23y_pilot_bar_is_fixed_white_and_always_visible():
    terminal = _pilot_terminal()

    assert "position:fixed;" in terminal
    assert "bottom:0;" in terminal
    assert "background:#ffffff;" in terminal
    assert "grid-template-columns:minmax(0, 1fr) 150px" in terminal
    assert "height:46px;" in terminal
    assert "min-height:46px;" in terminal
    assert "max-height:46px;" in terminal
    assert "Tell Pilot what to do..." in terminal


def test_phase23y_live_agents_surface_fills_viewport_white_to_hide_global_cream():
    surface = _live_agents_surface()

    assert "aion-phase23y-live-agents-white-shell" in surface
    assert "min-height:100vh" in surface
    assert "padding:42px 56px 96px 96px" in surface
    assert "background:#ffffff" in surface
    assert "background-color:#ffffff" in surface
    assert 'document.body.classList.add("aion-phase23y-live-agents-white")' in surface
    assert 'appRoot.style.background = "#ffffff";' in surface


def test_phase23y_white_surface_css_is_scoped_to_live_agents_body_class():
    assert "ensureAionPhase23YLiveAgentsWhiteSurfaceStyles" in APP_JS
    assert "body.aion-phase23y-live-agents-white" in APP_JS
    assert ".aion-phase23y-live-agents-white-shell" in APP_JS
    assert "background:#ffffff !important;" in APP_JS
    assert "background-color:#ffffff !important;" in APP_JS


def test_phase23y_no_big_persistent_terminal_header_panel():
    terminal = _pilot_terminal()

    assert "Persistent Pilot Terminal" not in terminal
    assert "AION works from here; departments are visible workspaces." not in terminal
    assert "Preview only" not in terminal
    assert "No live side effects" not in terminal
    assert "data-aion-phase23y-persistent-pilot-toggle" not in terminal


def test_phase23y_marketing_workspace_has_manual_and_pilot_tabs():
    assert "function renderLiveAgentsMarketingWorkspaceTabs" in APP_JS
    assert 'data-aion-marketing-workspace-mode="manual"' in APP_JS
    assert 'data-aion-marketing-workspace-mode="pilot"' in APP_JS
    assert "Manual" in APP_JS
    assert "Pilot Marketing" in APP_JS


def test_phase23y_marketing_branch_uses_unified_operational_workspace():
    body = _live_agents_workspace_body()
    branch_start = body.index('if (departmentKey === "marketing")')
    finance_start = body.index('if (departmentKey === "finance")', branch_start)
    branch = body[branch_start:finance_start]

    assert "return renderPilotMarketingWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);" in branch
    assert 'renderAionDepartmentPilotRuntime("marketing"' not in branch


def test_phase23y_pilot_marketing_workspace_surfaces_pilot_outputs():
    assert "function getAionPilotMarketingWorkspaceArtifacts" in APP_JS
    assert "data-aion-phase23y-pilot-marketing-workspace" in APP_JS
    assert "data-aion-phase23y-pilot-marketing-artifact-card" in APP_JS
    assert "tool_execution_queue" in APP_JS
    assert "step_outputs" in APP_JS


def test_phase23y_manual_workspace_is_consolidated_into_the_governed_studio():
    assert "function renderMarketingManualWorkspaceSurface" in APP_JS
    assert "return renderPilotMarketingWorkspaceSurface([], null);" in APP_JS
    assert "renderMarketingStreamSurface({ embedded: true })" in APP_JS
    assert 'data-aion-marketing-automation-studio="true"' in APP_JS
    assert 'data-aion-marketing-creation-studio=' in APP_JS


def test_phase23y_persistent_pilot_bar_can_start_task():
    assert "data-aion-phase23y-persistent-pilot-start" in APP_JS
    assert "createAionPilotFrontendDraftMission();" in APP_JS
    assert "pilotState.last_request = value;" in APP_JS


def test_phase23y_handlers_are_direct_and_stop_propagation():
    assert "__aionPhase23YMarketingWorkspaceHandlersInstalled" in APP_JS
    assert "event.stopPropagation();" in APP_JS
    assert "state.liveAgentsMarketingWorkspaceMode" in APP_JS


def test_phase23z_pilot_marketing_workspace_groups_deliverables():
    assert "function classifyAionPilotMarketingArtifact" in APP_JS
    assert "function groupAionPilotMarketingArtifacts" in APP_JS
    assert "data-aion-phase23z-pilot-marketing-deliverable-group" in APP_JS
    assert "data-aion-phase23z-pilot-marketing-deliverable-card" in APP_JS
    assert "Strategy" in APP_JS
    assert "Messaging" in APP_JS
    assert "Marketing plan" in APP_JS
    assert "Lead flow" in APP_JS
    assert "Blocked live actions" in APP_JS


def test_phase23z_global_cream_background_is_removed_from_theme_base():
    css = Path("desktop/mac/src/styles.css").read_text()

    assert "--aion-cream: #ffffff;" in css
    assert "--aion-cream-soft: #ffffff;" in css
    assert "--ft-bg: #ffffff;" in css
    assert "--ft-bg-soft: #ffffff;" in css


def test_phase23z_live_agents_white_surface_overrides_pseudo_elements():
    assert "body.aion-phase23y-live-agents-white::before" in APP_JS
    assert "body.aion-phase23y-live-agents-white::after" in APP_JS
    assert "html," in APP_JS
    assert "#app," in APP_JS
    assert "background:#ffffff !important;" in APP_JS
