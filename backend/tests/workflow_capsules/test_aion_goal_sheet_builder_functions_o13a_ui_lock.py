from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13A GOAL SHEET BUILDER FUNCTIONS" in APP_JS
    return APP_JS.split("BEGIN AION O13A GOAL SHEET BUILDER FUNCTIONS", 1)[1].split(
        "END AION O13A GOAL SHEET BUILDER FUNCTIONS", 1
    )[0]


def test_o13a_installed():
    b = block()
    assert "Goal Sheet builder functions installed" in b
    assert "aionBuildBoardroomGoalSheetGraphO13A" in b
    assert "aionBuildDepartmentGoalSheetGraphO13A" in b


def test_o13a_boardroom_parent_is_small_clean_sheet():
    b = block()
    assert 'canvas_type: "boardroom_goal_sheet"' in b
    assert "goal_sheet_meeting_minutes" in b
    assert "goal_sheet_board_decision" in b
    assert "goal_sheet_actual_goal" in b
    assert "goal_sheet_success_criteria" in b
    assert "goal_sheet_department_links" in b
    assert "goal_sheet_pilot_queue_preview" in b
    assert "goal_sheet_evidence_feedback" in b


def test_o13a_boardroom_parent_does_not_dump_department_chains():
    b = block()
    boardroom_builder = b.split("function buildBoardroomGoalSheetGraphO13A", 1)[1].split(
        "function buildDepartmentGoalSheetGraphO13A", 1
    )[0]
    assert "Linked department sheets" in boardroom_builder
    assert "linkedDepartmentSheets" in boardroom_builder
    assert "marketing assignment" not in boardroom_builder.lower()
    assert "sales assignment" not in boardroom_builder.lower()
    assert "finance assignment" not in boardroom_builder.lower()
    assert "operations assignment" not in boardroom_builder.lower()
    assert "support assignment" not in boardroom_builder.lower()


def test_o13a_department_sheets_are_separate_child_graphs():
    b = block()
    assert 'canvas_type: "department_goal_sheet"' in b
    assert "workflow_goal_loop_${safeDepartment}_goal_sheet" in b
    assert "department_goal" in b
    assert "department_plan" in b
    assert "department_pilot_tasks" in b
    assert "department_measurement" in b
    assert "department_evidence_feedback" in b


def test_o13a_all_departments_have_pilot_owners():
    b = block()
    assert 'pilot_owner: "marketing_pilot"' in b
    assert 'pilot_owner: "sales_pilot"' in b
    assert 'pilot_owner: "finance_pilot"' in b
    assert 'pilot_owner: "operations_pilot"' in b
    assert 'pilot_owner: "support_pilot"' in b


def test_o13a_registers_linked_workflow_registry():
    b = block()
    assert "registerGoalSheetGraphsO13A" in b
    assert "window.__aionGoalLoopDepartmentGoalSheets" in b
    assert "window.__aionGoalLoopLinkedWorkflowRegistry" in b
    assert "window.__aionO13ABoardroomGoalSheetGraph" in b


def test_o13a_safety_flags_are_preview_only():
    b = block()
    assert "makeGoalSheetSafetyO13A" in b
    assert "preview_only: true" in b
    assert "execution_allowed_now: false" in b
    assert "connector_call_required: false" in b
    assert "external_side_effects: false" in b
    assert "approval_required: true" in b
    assert "creates_second_canvas: false" in b
    assert "creates_second_pilot: false" in b


def test_o13a_has_document_payload_builder():
    b = block()
    assert "buildGoalSheetDocumentPayloadO13A" in b
    assert "meeting_minutes" in b
    assert "boardroom_decision" in b
    assert "actual_goal" in b
    assert "success_criteria" in b
    assert "linked_department_sheets" in b
    assert "pilot_queue_preview" in b
    assert "evidence_feedback" in b
