from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def o13l_block():
    return APP_JS[
        APP_JS.index("BEGIN AION O13L GOAL SHEET WORKFLOW TAB REGISTRY LOCK"):
        APP_JS.index("END AION O13L GOAL SHEET WORKFLOW TAB REGISTRY LOCK")
    ]


def test_o13l_goal_sheet_tab_registry_block_exists():
    assert "BEGIN AION O13L GOAL SHEET WORKFLOW TAB REGISTRY LOCK" in APP_JS
    assert "END AION O13L GOAL SHEET WORKFLOW TAB REGISTRY LOCK" in APP_JS
    assert "O13L.2 exact fix" in o13l_block()


def test_o13l_uses_existing_phase19b_workflow_tabs_store_without_second_canvas():
    block = o13l_block()

    assert "window.__aionWorkflowTabs" in block
    assert "window.__aionRenderWorkflowCanvasTabs" in block
    assert "creates_second_canvas = false" in block
    assert "creates_second_pilot = false" in block


def test_o13l_does_not_preopen_all_department_tabs():
    block = o13l_block()

    assert "ensureBoardroomTabO13L" in block
    assert "registerOpenedGoalSheetO13L" in block
    assert "DEPARTMENTS.forEach" not in block
    assert "opened-only" in block


def test_o13l_tab_click_loads_clicked_tab_graph():
    block = o13l_block()

    assert "getGraphForTabIdO13L" in block
    assert "activateGraphO13L(graph" in block
    assert "data-aion-workflow-main-tab-select" in block
    assert "data-aion-workflow-tab" in block
    assert "event.stopImmediatePropagation" in block


def test_o13l_wraps_existing_department_openers_and_select():
    block = o13l_block()

    assert "previousOpenO13B" in block
    assert "previousOpenO13I" in block
    assert "window.aionOpenDepartmentGoalSheetO13B = wrappedO13B" in block
    assert "window.aionOpenDepartmentGoalSheetO13I = wrappedO13I" in block
    assert "previousSelect" in block
    assert "window.__aionSelectWorkflowCanvasTab = wrappedSelect" in block
