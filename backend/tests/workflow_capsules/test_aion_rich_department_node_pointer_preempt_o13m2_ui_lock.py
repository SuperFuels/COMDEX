from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def o13m2_block():
    start = APP_JS.index("BEGIN AION O13M2 RICH DEPARTMENT NODE POINTER PREEMPT LOCK")
    end = APP_JS.index("END AION O13M2 RICH DEPARTMENT NODE POINTER PREEMPT LOCK")
    return APP_JS[start:end]


def test_o13m2_preempts_pointer_events_before_o13k_document_router():
    block = o13m2_block()

    assert '"pointerdown", "mousedown", "click", "dblclick"' in block
    assert "window.addEventListener(eventName, routeRichDepartmentNodeO13M2, true)" in block
    assert "event.stopImmediatePropagation" in block


def test_o13m2_routes_to_rich_o13m_renderer_and_removes_thin_modal():
    block = o13m2_block()

    assert "aionOpenDepartmentGoalSheetNodeDocumentO13M" in block
    assert "aion-o13k-department-goal-sheet-node-preview" in block
    assert "removeThinDepartmentModalO13M2" in block
    assert "aionRouteRichDepartmentNodeDocumentO13M2" in block


def test_o13m2_covers_department_goal_sheet_node_types():
    block = o13m2_block()

    for node_type in [
        "department_goal",
        "department_plan",
        "pilot_task_queue",
        "department_pilot_tasks",
        "department_measurement",
        "department_evidence_feedback",
        "evidence_back_to_boardroom",
    ]:
        assert node_type in block
