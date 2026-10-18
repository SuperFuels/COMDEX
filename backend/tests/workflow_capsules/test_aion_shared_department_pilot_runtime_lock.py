from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
RUNTIME = (ROOT / "desktop/mac/src/aion_department_pilot_runtime.js").read_text(encoding="utf-8")
FINANCE = (ROOT / "desktop/mac/src/aion_finance_pilot.js").read_text(encoding="utf-8")


def function_block(name: str) -> str:
    start = APP.index(f"function {name}")
    end = APP.find("\nfunction ", start + len(name) + 9)
    return APP[start:] if end == -1 else APP[start:end]


def test_shared_runtime_is_modular_and_loaded_before_app():
    assert "aion_department_pilot_runtime.js" in INDEX
    assert INDEX.index("aion_department_pilot_runtime.js") < INDEX.index("app.js")
    assert "global.AionDepartmentPilotRuntime" in RUNTIME
    for pilot_id in (
        "marketing_pilot",
        "sales_pilot",
        "finance_pilot",
        "operations_pilot",
        "support_pilot",
        "hr_pilot",
        "central_pilot",
    ):
        assert pilot_id in RUNTIME


def test_hr_has_navigation_profile_route_and_goal_loop_scope():
    nav = function_block("renderLiveAgentsExecutiveDepartmentNavO14P")
    resolver = function_block("getSelectedLiveDepartmentKey")
    normalizer = function_block("normaliseAionDepartmentPilotKey")
    assert '["hr", "HR"]' in nav
    assert '"hr"' in resolver
    assert '["marketing", "sales", "finance", "operations", "support", "hr"]' in normalizer
    assert 'title: "HR Pilot"' in APP
    assert 'title: "HR Specialist Pilot"' in APP
    assert '"hr_pilot"' in APP
    assert '"support",\n  "hr",' in APP


def test_department_tabs_open_one_shared_pilot_conversation():
    route = function_block("renderLiveAgentsWorkspaceBody")
    card = function_block("renderDepartmentCompactDirectorCard")
    conversation = function_block("openUnifiedDepartmentPilotConversation")
    shared = function_block("renderAionDepartmentPilotRuntime")
    stream = function_block("renderAionPilotSimpleTaskStream")
    for renderer in (
        "renderPilotMarketingWorkspaceSurface",
        "renderSalesWorkspaceSurface",
        "renderFinanceWorkspaceSurface",
        "renderOperationsWorkspaceSurface",
        "renderSupportWorkspaceSurface",
        "renderHRWorkspaceSurface",
    ):
        assert renderer in route
    assert 'data-aion-unified-department-conversation=' in card
    assert "renderAionO18AADepartmentConversationCockpit" in conversation
    assert "renderAionPilotSimpleTaskStream" in shared
    assert 'data-aion-shared-pilot-terminal="true"' in stream
    assert "AionDepartmentPilotRuntime?.getContext" in stream
    assert "department_scope" in stream


def test_live_agents_department_navigation_is_borderless_and_left_aligned():
    nav = function_block("renderLiveAgentsExecutiveDepartmentNavO14P")
    surface = function_block("renderLiveAgentsSurface")
    assert "position:sticky" in nav
    assert "flex-direction:row" in nav
    assert "justify-content:flex-start" in nav
    assert "border:0" in nav
    assert '"#e8f2ff"' in nav
    assert "padding:32px 48px 96px 96px" in surface
    assert '[data-aion-o14p-live-agents-top-nav="true"] button:hover' in APP
    assert "background:#f0f6ff !important" in APP
    assert "outline:0 !important" in APP
    assert "@media (max-width: 1120px)" in APP


def test_each_department_has_isolated_persistent_runtime_state():
    state = function_block("getAionPilotFrontendInteractionState")
    assert "__aionPilotFrontendInteractionStates" in state
    assert "aion.pilot.runtimeState.${scope}.v1" in state
    assert "getAionPilotActiveDepartmentScope" in state


def test_finance_setup_hands_over_to_shared_runtime_when_complete():
    assert "state.status === 'complete'" in FINANCE
    assert "global.renderAionDepartmentPilotRuntime('finance')" in FINANCE


def test_central_pilot_default_page_is_clean_stream_not_goal_loop_debug_stack():
    central = function_block("renderAionWorkspaceSurface")
    assert "renderAionPilotCockpitPanel" in central
    assert "renderAionGoalLoopFounderDemoTracePanel" not in central
    assert "renderAionGoalLoopMeasurementSchemaPanel" not in central
    assert "renderAionGoalLoopBusinessContainerPersistencePanel" not in central


def test_redundant_global_fixed_command_bar_is_not_mounted():
    surface = function_block("renderLiveAgentsSurface")
    assert "renderLiveAgentsPersistentPilotTerminal()" not in surface
