from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13H4 LINKED DEPARTMENT RENDER NAVIGATION NODE" in APP_JS
    return APP_JS.split("BEGIN AION O13H4 LINKED DEPARTMENT RENDER NAVIGATION NODE", 1)[1].split(
        "END AION O13H4 LINKED DEPARTMENT RENDER NAVIGATION NODE", 1
    )[0]


def test_o13h4_installed():
    b = block()
    assert "Linked department render navigation node installed" in b
    assert "aionOpenLinkedDepartmentRouterO13H4" in b
    assert "aionClearGenericNodeEditorO13H4" in b


def test_o13h4_render_uses_navigation_attr_for_linked_department_node():
    assert "data-aion-goal-sheet-department-links-router" in APP_JS
    assert "goal_sheet_department_links" in APP_JS
    assert "department_goal_links" in APP_JS
    assert "linked_department_sheets" in APP_JS
    assert '? `data-aion-goal-sheet-department-links-router="' in APP_JS
    assert ': `data-aion-workflow-node-id="' in APP_JS


def test_o13h4_blocks_generic_editor_for_navigation_node():
    b = block()
    assert "generic_workflow_node_editor_blocked: true" in b
    assert "event.stopImmediatePropagation()" in b
    assert "window.__aionWorkflowSelectedNodeId = null" in b
    assert "window.__aionWorkflowInspectorOpen = false" in b


def test_o13h4_intercepts_early_and_double_click_events():
    b = block()
    assert '"pointerdown"' in b
    assert '"mousedown"' in b
    assert '"click"' in b
    assert '"dblclick"' in b


def test_o13h4_opens_existing_router_chain():
    b = block()
    assert "aionOpenLinkedDepartmentRouterO13H3" in b
    assert "aionRenderLinkedDepartmentSheetRouterO13H2" in b
    assert "aionRenderLinkedDepartmentSheetChooserO13H" in b
    assert "aionRenderDepartmentChooserO13B" in b
