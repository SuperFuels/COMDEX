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
    block = function_block("renderFinanceWorkspaceSurface")

    assert "renderAionRealFinance121BoardroomPanelV2()" in block
    assert "renderAionFinanceDataSetupPanelV2()" in block
    assert 'renderAionDepartmentScopedPilotSurface("finance", selectedRuns, selectedAgentCard)' in block


def test_sales_operations_support_route_to_department_scoped_pilot():
    assert 'function renderSalesWorkspaceSurface(selectedRuns, selectedAgentCard)' in APP_JS
    assert 'return renderAionDepartmentScopedPilotSurface("sales", selectedRuns, selectedAgentCard);' in APP_JS

    assert 'function renderOperationsWorkspaceSurface(selectedRuns, selectedAgentCard)' in APP_JS
    assert 'return renderAionDepartmentScopedPilotSurface("operations", selectedRuns, selectedAgentCard);' in APP_JS

    assert 'function renderSupportWorkspaceSurface(selectedRuns, selectedAgentCard)' in APP_JS
    assert 'return renderAionDepartmentScopedPilotSurface("support", selectedRuns, selectedAgentCard);' in APP_JS


def test_central_aion_workspace_stays_separate_guarded_executor():
    block = function_block("renderAionWorkspaceSurface")

    assert "AION Pilot — native AION runtime executor" in block
    assert "Plan-gated runtime. No live external side effects without exact approval." in block
    assert "renderAionPilotCockpitPanel" in block

    assert "renderAionDepartmentScopedPilotSurface" not in block
    assert "renderFinanceWorkspaceSurface" not in block
