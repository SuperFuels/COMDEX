from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o13h5_linked_department_router_render_attr_exists():
    assert "data-aion-goal-sheet-department-links-router" in APP_JS
    assert "goal_sheet_department_links" in APP_JS
    assert "department_goal_links" in APP_JS
    assert "linked_department_sheets" in APP_JS
    assert "linked department sheets" in APP_JS


def test_o13h5_generic_workflow_attr_only_exists_as_fallback_branch():
    assert ': `data-aion-workflow-node-id="' in APP_JS
    assert '? `data-aion-goal-sheet-department-links-router="' in APP_JS


def test_o13h5_render_decision_is_inline_not_window_dependent():
    render_area = APP_JS.split('class="aion-canvas-node', 1)[1].split('type="button"', 1)[0]
    assert "data-aion-goal-sheet-department-links-router" in render_area
    assert "aionIsLinkedDepartmentNavigationNodeO13H3(node)" not in render_area
    assert "node.data?.document_type" in render_area
    assert "node.config?.document_type" in render_area


def test_o13h5_navigation_node_cannot_open_generic_editor():
    assert "aionRouteLinkedDepartmentNavigationNodeO13H3" in APP_JS
    assert "window.__aionWorkflowSelectedNodeId = null" in APP_JS
    assert "window.__aionWorkflowInspectorOpen = false" in APP_JS
    assert "prevented_generic_parameters_editor: true" in APP_JS
