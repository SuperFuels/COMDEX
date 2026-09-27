from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12b_replaces_giant_department_canvas_with_boardroom_goal_sheet():
    assert "BEGIN AION O12B BOARDROOM GOAL SHEET ARCHITECTURE" in APP_JS
    assert "Boardroom Goal Sheet" in APP_JS
    assert "Linked department sheets" in APP_JS
    assert "Pilot queue preview" in APP_JS
    assert "department_goal_sheets" in APP_JS


def test_o12b_keeps_existing_canvas_and_pilot_safety_boundaries():
    assert "creates_second_canvas: false" in APP_JS
    assert "creates_second_pilot: false" in APP_JS
    assert "existing_workflow_canvas_reused: true" in APP_JS
    assert "existing_central_pilot_reused: true" in APP_JS
    assert "existing_department_pilots_reused: true" in APP_JS
    assert "no_live_execution: true" in APP_JS
    assert "no_connector_calls: true" in APP_JS


def test_o12b_creates_linked_department_goal_sheets_not_one_big_canvas():
    assert "buildDepartmentGoalSheetGraph" in APP_JS
    assert "workflow_goal_loop_${dept.key}_goal_sheet" in APP_JS
    assert "window.__aionGoalLoopLinkedWorkflowRegistry" in APP_JS
    assert "openLinkedWorkflow" in APP_JS
    assert "Department goal sheets are linked records, not dumped into the Boardroom canvas." in APP_JS


def test_o12b_clickable_goal_sheet_inspector_payloads_exist():
    assert "openGoalSheetInspector" in APP_JS
    assert "meeting_minutes" in APP_JS
    assert "Actual goal" in APP_JS
    assert "Success criteria" in APP_JS
    assert "Board decision" in APP_JS
    assert "data-aion-o12b-open-linked-workflow" in APP_JS


def test_o12b_secondary_canvas_sheet_is_suppressed():
    assert ".aion-workflow-canvas-viewport::before" in APP_JS
    assert "[data-aion-workflow-canvas-viewport='true']::after" in APP_JS
    assert "[class*=\"canvas-sheet\"]" in APP_JS
    assert "[class*=\"canvas-paper\"]" in APP_JS
    assert "background-image: none !important" in APP_JS


def test_o12b_staged_notice_is_dismissible_and_expires():
    assert "data-aion-o12b-dismiss-workflow-status" in APP_JS
    assert "dismissWorkflowStatus" in APP_JS
    assert "scheduleWorkflowStatusExpiry" in APP_JS
    assert "window.setTimeout(dismissWorkflowStatus, 7000)" in APP_JS
    assert "aion.boardroomGoalSheet.stagedNoticeDismissed.v1" in APP_JS
    assert "resetWorkflowStatusDismissal();" in APP_JS


def test_o11b_is_retired_by_o12b():
    assert "RETIRED BY O12B" in APP_JS
    assert "Goal Loop is now a Boardroom Goal Sheet with linked department sheets" in APP_JS
