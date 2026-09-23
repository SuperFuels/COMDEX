from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js").read_text()


def test_phase23x_pilot_branch_is_before_generic_runs_settings_intercepts():
    pilot_index = APP_JS.index('if (departmentKey === "pilot")')
    settings_index = APP_JS.index('if (activeView === LIVE_AGENT_VIEWS.SETTINGS)', pilot_index)
    runs_index = APP_JS.index('if (activeView === LIVE_AGENT_VIEWS.RUNS)', pilot_index)

    assert pilot_index < settings_index
    assert pilot_index < runs_index


def test_phase23x_pilot_branch_renders_original_aion_workspace_surface():
    pilot_start = APP_JS.index('if (departmentKey === "pilot")')
    finance_start = APP_JS.index('if (departmentKey === "finance")', pilot_start)
    pilot_branch = APP_JS[pilot_start:finance_start]

    assert 'return renderAionWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);' in pilot_branch
    assert 'return renderGenericDepartmentWorkspaceSurface' not in pilot_branch


def test_phase23x_original_pilot_surface_mount_still_exists():
    assert "function renderAionWorkspaceSurface" in APP_JS
    assert "data-aion-phase21l-live-agents-aion-pilot-mount" in APP_JS
    assert "renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())" in APP_JS
    assert 'data-aion-shared-pilot-terminal="true"' in APP_JS


def test_phase23x_pilot_uses_isolated_central_runtime_state():
    surface_start = APP_JS.index("function renderAionWorkspaceSurface")
    surface_end = APP_JS.index("/* PHASE 21L LOCK", surface_start)
    surface = APP_JS[surface_start:surface_end]

    assert "renderAionPilotCockpitPanel" in surface
    assert "renderAionGoalLoopMeasurementSchemaPanel" not in surface


def test_phase23x_minimal_department_switcher_uses_fast_direct_handler():
    assert "data-aion-minimal-department-switch" in APP_JS
    assert "__aionMinimalDepartmentSwitcherFastHandlerInstalled" in APP_JS
    assert "state.selectedLiveDepartmentKey = departmentKey;" in APP_JS
    assert "state.liveAgentsView = LIVE_AGENT_VIEWS.STREAM;" in APP_JS
    assert "event.stopPropagation();" in APP_JS


def test_phase23x_mission_preview_payload_builds_work_package_before_approval_stages():
    fn_start = APP_JS.index("function buildAionPilotMissionPreviewPayload")
    fn_end = APP_JS.index("function applyAionPilotMissionPreviewPayload", fn_start)
    fn = APP_JS[fn_start:fn_end]

    work_package_index = fn.index("const workPackage")
    approval_index = fn.index("const approvalStages")

    assert work_package_index < approval_index
    assert "getAionPilotApprovalStagePayload(workPackage, state)" not in fn[:work_package_index]
    assert "approval_stage_details: draftSteps" in fn
    assert fn.count("approval_stages:") == 1
