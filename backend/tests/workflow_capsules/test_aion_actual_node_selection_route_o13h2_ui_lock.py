from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13H2 ACTUAL NODE SELECTION ROUTE FOR LINKED DEPARTMENT SHEETS" in APP_JS
    return APP_JS.split("BEGIN AION O13H2 ACTUAL NODE SELECTION ROUTE FOR LINKED DEPARTMENT SHEETS", 1)[1].split(
        "END AION O13H2 ACTUAL NODE SELECTION ROUTE FOR LINKED DEPARTMENT SHEETS", 1
    )[0]


def test_o13h2_installed():
    b = block()
    assert "actual workflow node selection route installed" in b
    assert "aionShouldRouteLinkedDepartmentNodeO13H2" in b
    assert "aionRouteLinkedDepartmentNodeO13H2" in b


def test_o13h2_detects_linked_department_node_from_real_graph_record():
    b = block()
    assert "getNodeRecordO13H2" in b
    assert "goal_sheet_department_links" in b
    assert "department_goal_links" in b
    assert "linked_department_sheets" in b
    assert "linked department sheets" in b


def test_o13h2_prevents_generic_node_editor_state():
    b = block()
    assert "closeActualWorkflowNodeEditorO13H2" in b
    assert "window.__aionWorkflowSelectedNodeId = null" in b
    assert "window.__aionWorkflowInspectorOpen = false" in b
    assert "prevented_generic_node_editor: true" in b


def test_o13h2_renders_real_department_sheet_router():
    b = block()
    assert "aion-o13h2-linked-department-sheet-router" in b
    assert "Pick a department Goal Sheet" in b
    assert "This node is not a normal workflow parameter step" in b
    assert "data-aion-o13h2-open-department" in b


def test_o13h2_opens_department_sheet_not_parameters_editor():
    b = block()
    assert "aionOpenDepartmentGoalSheetO13B" in b
    assert "aionBuildDepartmentGoalSheetGraphO13A" in b
    assert "window.__aionWorkflowGraph = sheet" in b
    assert "window.__aionWorkflowInspectorOpen = false" in b


def test_o13h2_supports_all_departments():
    b = block()
    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'"{department}"' in b


def test_o13h2_actual_selection_handlers_have_guard():
    assert "window.aionRouteLinkedDepartmentNodeO13H2(nodeId, nodeEl)" in APP_JS
    assert "window.aionRouteLinkedDepartmentNodeO13H2(nodeId, node)" in APP_JS
    assert "event.stopImmediatePropagation()" in APP_JS
