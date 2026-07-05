from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O13N1 FORCE DEPARTMENT NODE ROUTES THROUGH BOARDROOM DRIVEN DOCS")
    end = APP_JS.index("END AION O13N1 FORCE DEPARTMENT NODE ROUTES THROUGH BOARDROOM DRIVEN DOCS")
    return APP_JS[start:end]


def test_o13n1_wraps_old_o13m_and_o13k_routes():
    b = block()

    assert "previousO13MOpen" in b
    assert "window.aionOpenDepartmentGoalSheetNodeDocumentO13M" in b
    assert "previousO13KRender" in b
    assert "window.aionRenderDepartmentGoalSheetNodePreviewO13K" in b
    assert "aionOpenBoardroomDrivenDepartmentDocumentO13N" in b


def test_o13n1_preempts_department_node_clicks_before_old_handlers():
    b = block()

    assert '"pointerdown", "mousedown", "click", "dblclick"' in b
    assert "window.addEventListener(eventName, preemptDepartmentNodeClickO13N1, true)" in b
    assert "document.addEventListener(eventName, preemptDepartmentNodeClickO13N1, true)" in b
    assert "event.stopImmediatePropagation" in b


def test_o13n1_removes_old_thin_modals():
    b = block()

    assert "aion-o13k-department-goal-sheet-node-preview" in b
    assert "aion-o13m-department-goal-sheet-node-document" in b
    assert "removeOldDepartmentModalsO13N1" in b
