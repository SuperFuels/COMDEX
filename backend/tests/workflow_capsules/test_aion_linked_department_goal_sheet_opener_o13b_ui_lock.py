from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13B LINKED DEPARTMENT GOAL SHEET OPENER" in APP_JS
    return APP_JS.split("BEGIN AION O13B LINKED DEPARTMENT GOAL SHEET OPENER", 1)[1].split(
        "END AION O13B LINKED DEPARTMENT GOAL SHEET OPENER", 1
    )[0]


def test_o13b_installed():
    b = block()
    assert "linked department Goal Sheet opener installed" in b
    assert "aionOpenDepartmentGoalSheetO13B" in b
    assert "aionOpenBoardroomGoalSheetO13B" in b


def test_o13b_ensures_department_registry():
    b = block()
    assert "ensureDepartmentSheetRegistryO13B" in b
    assert "window.__aionGoalLoopDepartmentGoalSheets" in b
    assert "window.__aionGoalLoopLinkedWorkflowRegistry" in b
    assert "aionBuildAllDepartmentGoalSheetsO13A" in b


def test_o13b_opens_department_graph_into_canvas_sources():
    b = block()
    assert "syncGraphToCanvasO13B" in b
    assert "window.__aionWorkflowGraph = graph" in b
    assert "window.__aionGoalLoopWorkflowGraph = graph" in b
    assert "window.__aionSelectedWorkflowId = graph.workflow_id" in b
    assert "requestRender()" in b


def test_o13b_does_not_persist_preview_switch_to_localstorage():
    b = block()
    assert "Do not persist here" in b
    assert "localStorage" in b
    assert "Persistence belongs to the business" in b


def test_o13b_has_department_chooser_for_linked_node():
    b = block()
    assert "renderDepartmentChooserO13B" in b
    assert "data-aion-o13b-department-sheet-chooser" in b
    assert "data-aion-o13b-open-department-sheet" in b
    assert "Linked child sheets" in b


def test_o13b_intercepts_linked_department_node_click_only():
    b = block()
    assert "maybeOpenDepartmentChooserFromNodeO13B" in b
    assert "linked_department_sheets" in b
    assert "department_links" in b
    assert '[data-aion-workflow-node-id]' in b
    assert "event.stopImmediatePropagation()" in b


def test_o13b_supports_all_five_departments():
    b = block()
    assert '"marketing"' in b
    assert '"sales"' in b
    assert '"finance"' in b
    assert '"operations"' in b
    assert '"support"' in b


def test_o13b_preview_safety_flags_remain_blocked():
    b = block()
    assert "preview_only = true" in b
    assert "execution_allowed_now = false" in b
    assert "connector_call_required = false" in b
    assert "external_side_effects = false" in b
    assert "creates_second_canvas = false" in b
    assert "creates_second_pilot = false" in b
