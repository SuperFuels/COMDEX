from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13I DEPARTMENT GOAL SHEET OPEN UX FIX" in APP_JS
    return APP_JS.split("BEGIN AION O13I DEPARTMENT GOAL SHEET OPEN UX FIX", 1)[1].split(
        "END AION O13I DEPARTMENT GOAL SHEET OPEN UX FIX", 1
    )[0]


def test_o13i_installed():
    b = block()
    assert "department Goal Sheet open UX fix installed" in b
    assert "aionOpenDepartmentGoalSheetO13I" in b
    assert "aionCloseGoalSheetChooserAndPreviewPanelsO13I" in b


def test_o13i_closes_offscreen_preview_and_chooser():
    b = block()
    assert "aion-o13d-live-agents-pilot-preview" in b
    assert "aion-o13h3-linked-department-router" in b
    assert "aion-o13b-department-sheet-chooser" in b
    assert "closeChooserAndPreviewPanelsO13I" in b


def test_o13i_forces_department_sheet_into_canvas_state():
    b = block()
    assert "window.__aionWorkflowGraph = sheet" in b
    assert "window.__aionGoalLoopWorkflowGraph = sheet" in b
    assert "window.__aionSelectedWorkflowId = sheet.workflow_id" in b
    assert "window.__aionWorkflowSelectedNodeId = null" in b


def test_o13i_intercepts_all_department_buttons():
    b = block()
    assert "data-aion-o13h3-department" in b
    assert "data-aion-o13h2-open-department" in b
    assert "data-aion-o13b-open-department-sheet" in b
    assert "event.stopImmediatePropagation()" in b


def test_o13i_supports_all_departments():
    b = block()
    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'"{department}"' in b


def test_o13i_builds_active_pilot_packets_after_open():
    b = block()
    assert "aionBuildActiveDepartmentPilotTaskPacketsO13C" in b
    assert "__aionO13ILastOpenedDepartmentGoalSheet" in b
