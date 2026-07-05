from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13H LINKED DEPARTMENT SHEETS CLICK ROUTING FIX" in APP_JS
    return APP_JS.split("BEGIN AION O13H LINKED DEPARTMENT SHEETS CLICK ROUTING FIX", 1)[1].split(
        "END AION O13H LINKED DEPARTMENT SHEETS CLICK ROUTING FIX", 1
    )[0]


def test_o13h_installed():
    b = block()
    assert "Linked department sheets click routing fix installed" in b
    assert "aionRenderLinkedDepartmentSheetChooserO13H" in b
    assert "aionOpenDepartmentSheetFromChooserO13H" in b


def test_o13h_detects_linked_department_node_by_id_and_text():
    b = block()
    assert "isLinkedDepartmentSheetsClickO13H" in b
    assert "department_links" in b
    assert "linked_department_sheets" in b
    assert "linked department sheets" in b
    assert "department sheets" in b


def test_o13h_intercepts_early_events_before_generic_node_editor():
    b = block()
    assert '"pointerdown"' in b
    assert '"mousedown"' in b
    assert '"click"' in b
    assert "event.stopImmediatePropagation()" in b
    assert "legacy node editor can" in b


def test_o13h_closes_generic_node_editor():
    b = block()
    assert "closeGenericNodeEditorO13H" in b
    assert ".node-editor" in b
    assert "window.__aionWorkflowInspectorOpen = false" in b


def test_o13h_renders_department_chooser():
    b = block()
    assert "aion-o13h-linked-department-chooser" in b
    assert "Pick a department Goal Sheet" in b
    assert "data-aion-o13h-open-department" in b


def test_o13h_opens_department_sheet_using_o13b():
    b = block()
    assert "aionOpenDepartmentGoalSheetO13B" in b
    assert "aionBuildDepartmentGoalSheetGraphO13A" in b
    assert "window.__aionWorkflowGraph = sheet" in b


def test_o13h_supports_all_departments():
    b = block()
    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'"{department}"' in b
