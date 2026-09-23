from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13H3 LINKED DEPARTMENT NODE IS NAVIGATION NOT EDITOR" in APP_JS
    return APP_JS.split("BEGIN AION O13H3 LINKED DEPARTMENT NODE IS NAVIGATION NOT EDITOR", 1)[1].split(
        "END AION O13H3 LINKED DEPARTMENT NODE IS NAVIGATION NOT EDITOR", 1
    )[0]


def test_o13h3_installed():
    b = block()
    assert "Linked department node is navigation not editor installed" in b
    assert "aionIsLinkedDepartmentNavigationNodeO13H3" in b
    assert "aionRouteLinkedDepartmentNavigationNodeO13H3" in b


def test_o13h3_treats_node_as_navigation_not_editor():
    b = block()
    assert "This is a navigation node, not a workflow parameter step" in b
    assert "prevented_generic_parameters_editor: true" in b
    assert "window.__aionWorkflowInspectorOpen = false" in b


def test_o13h3_router_has_department_choices():
    b = block()
    assert "Pick a department Goal Sheet" in b
    assert "data-aion-o13h3-department" in b
    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'"{department}"' in b


def test_o13h3_opens_department_goal_sheet():
    b = block()
    assert "aionOpenDepartmentGoalSheetO13B" in b
    assert "aionBuildDepartmentGoalSheetGraphO13A" in b
    assert "window.__aionWorkflowGraph = sheet" in b


def test_o13h3_patches_selected_node_assignments():
    assert "window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)" in APP_JS
    assert "window.aionRouteLinkedDepartmentNavigationNodeO13H3(node)" in APP_JS
    assert "window.__aionWorkflowSelectedNodeId = null" in APP_JS
    assert "window.__aionWorkflowInspectorOpen = false" in APP_JS


def test_o13h1_observer_workaround_disabled():
    assert "DISABLED BY O13H3" in APP_JS
    assert "installAionO13H1LinkedDepartmentDocumentBoxReroute_DISABLED_BY_O13H3" in APP_JS
