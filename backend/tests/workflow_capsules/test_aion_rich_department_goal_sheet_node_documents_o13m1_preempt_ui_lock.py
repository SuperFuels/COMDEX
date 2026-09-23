from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O13M1 RICH DEPARTMENT NODE DOCUMENT PREEMPT ROUTER")
    end = APP_JS.index("END AION O13M1 RICH DEPARTMENT NODE DOCUMENT PREEMPT ROUTER", start)
    return APP_JS[start:end]


def test_o13m1_uses_window_capture_before_document_o13k():
    b = block()

    assert 'window.addEventListener("click", routeRichDepartmentNodeO13M1, true)' in b
    assert "event.stopImmediatePropagation" in b
    assert "aionOpenDepartmentGoalSheetNodeDocumentO13M" in b


def test_o13m1_targets_department_goal_sheet_nodes_only():
    b = block()

    assert "isDepartmentGoalSheetGraphO13M1" in b
    assert "department_goal_sheet" in b
    assert "department_goal" in b
    assert "department_plan" in b
    assert "department_pilot_tasks" in b
    assert "department_measurement" in b
    assert "department_evidence_feedback" in b


def test_o13m1_removes_old_thin_o13k_modal_if_present():
    b = block()

    assert "aion-o13k-department-goal-sheet-node-preview" in b
    assert "data-aion-o13k-department-node-preview" in b
    assert "window.__aionWorkflowInspectorOpen = false" in b
