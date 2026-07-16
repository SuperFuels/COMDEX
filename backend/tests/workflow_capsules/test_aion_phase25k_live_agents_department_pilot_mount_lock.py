from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name: str) -> str:
    marker = f"function {name}"
    start = APP_JS.index(marker)
    next_function = APP_JS.find("\nfunction ", start + len(marker))
    if next_function == -1:
        return APP_JS[start:]
    return APP_JS[start:next_function]


def test_marketing_workspace_mounts_scoped_pilot_once_without_duplicate_phase25_panels():
    block = function_block("renderPilotMarketingWorkspaceSurface")

    assert 'renderAionDepartmentScopedPilotSurface("marketing", selectedRuns, selectedAgentCard)' in block
    assert block.count('renderAionDepartmentScopedPilotSurface("marketing", selectedRuns, selectedAgentCard)') == 1

    assert 'renderAionDepartmentPilotPhase25CPanel("marketing")' not in block
    assert 'renderAionDepartmentPilotPhase25DPanel("marketing")' not in block
    assert 'renderAionDepartmentPilotPhase25EPanel("marketing")' not in block
    assert 'renderAionDepartmentPilotPhase25FPanel("marketing")' not in block


def test_finance_workspace_keeps_finance_room_setup_and_scoped_pilot():
    finance = Path("desktop/mac/src/aion_finance_pilot.js").read_text(encoding="utf-8")
    assert "state.status === 'complete'" in finance
    assert "global.renderAionDepartmentPilotRuntime('finance')" in finance


def test_sales_operations_support_and_hr_route_to_shared_department_pilot():
    block = function_block("renderLiveAgentsWorkspaceBody")
    assert '["marketing", "sales", "operations", "support", "hr"].includes(departmentKey)' in block
    assert "renderAionDepartmentPilotRuntime(departmentKey" in block


def test_central_aion_workspace_stays_separate_guarded_executor():
    block = function_block("renderAionWorkspaceSurface")

    assert "renderAionPilotCockpitPanel" in block
    assert "renderAionGoalLoopFounderDemoTracePanel" not in block

    assert "renderAionDepartmentScopedPilotSurface" not in block
    assert "renderFinanceWorkspaceSurface" not in block
