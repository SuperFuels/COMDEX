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

    assert 'return renderAionWorkspaceSurface(selectedRuns, selectedAgentCard);' in pilot_branch
    assert 'return renderGenericDepartmentWorkspaceSurface' not in pilot_branch


def test_phase23x_original_pilot_surface_mount_still_exists():
    assert "function renderAionWorkspaceSurface" in APP_JS
    assert "data-aion-phase21l-live-agents-aion-pilot-mount" in APP_JS
    assert "renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())" in APP_JS
    assert "Live Agents / Pilot" in APP_JS


def test_phase23x_pilot_counts_use_pilot_department_not_legacy_aion():
    surface_start = APP_JS.index("function renderAionWorkspaceSurface")
    surface_end = APP_JS.index("/* PHASE 21L LOCK", surface_start)
    surface = APP_JS[surface_start:surface_end]

    assert 'getDepartmentRunCounts("pilot")' in surface
    assert 'getDepartmentRunCounts("aion")' not in surface
