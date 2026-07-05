from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o13i1_patches_actual_o13b_opener():
    assert "function openDepartmentGoalSheetO13B(department)" in APP_JS
    assert "O13B/O13I.1 opened department Goal Sheet visibly" in APP_JS
    assert "active_canvas_forced: true" in APP_JS


def test_o13i1_forces_all_active_canvas_slots():
    assert "window.__aionWorkflowGraph = sheet" in APP_JS
    assert "window.__aionActiveWorkflowGraph = sheet" in APP_JS
    assert "window.__aionGoalLoopWorkflowGraph = sheet" in APP_JS
    assert "window.__aionSelectedWorkflowId = sheet.workflow_id" in APP_JS
    assert "window.__aionActiveWorkflowId = sheet.workflow_id" in APP_JS


def test_o13i1_closes_chooser_and_preview_panels():
    assert "aion-o13h3-linked-department-router" in APP_JS
    assert "aion-o13b-department-sheet-chooser" in APP_JS
    assert "aion-o13d-live-agents-pilot-preview" in APP_JS
    assert "chooser_closed: true" in APP_JS


def test_o13i1_resets_viewport_and_selection():
    assert "window.__aionWorkflowUserViewportLocked = false" in APP_JS
    assert "window.__aionWorkflowViewport" in APP_JS
    assert "window.__aionWorkflowSelectedNodeId = null" in APP_JS
    assert "window.__aionWorkflowInspectorOpen = false" in APP_JS
