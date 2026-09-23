from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O13L3 GOAL SHEET TAB CLICK ROUTER PREEMPT LOCK")
    end = APP_JS.index("END AION O13L3 GOAL SHEET TAB CLICK ROUTER PREEMPT LOCK")
    return APP_JS[start:end]


def test_o13l3_installed_as_window_capture_preempt():
    text = block()
    assert "O13L.3 exact fix" in text
    assert "window.addEventListener(eventName, handleGoalSheetTabClickO13L3, true)" in text
    assert "event.stopImmediatePropagation" in text


def test_o13l3_boardroom_tab_resolves_real_boardroom_graph():
    text = block()
    assert "boardroomGraphO13L3" in text
    assert "window.__aionBoardroomGoalSheetGraph" in text
    assert "window.__aionO13ABoardroomGoalSheetGraph" in text
    assert 'hay.includes("boardroom")' in text
    assert 'hay.includes("goal loop")' in text


def test_o13l3_department_tabs_resolve_department_graphs():
    text = block()
    assert "departmentGraphByIdO13L3" in text
    assert '["marketing", "sales", "finance", "operations", "support"]' in text
    assert "window.__aionGoalLoopDepartmentGoalSheets" in text
    assert "window.__aionO13ADepartmentGoalSheets" in text


def test_o13l3_activation_updates_existing_canvas_slots():
    text = block()
    assert "window.__aionWorkflowGraph = safeGraph" in text
    assert "window.__aionWorkflowMainGraph = safeGraph" in text
    assert "window.__aionActiveWorkflowGraph = safeGraph" in text
    assert "window.__aionActiveWorkflowTabId" in text
    assert "requestRender" in text
