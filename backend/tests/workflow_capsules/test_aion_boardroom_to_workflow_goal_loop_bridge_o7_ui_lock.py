from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o7_boardroom_bridge_now_stages_o12b_goal_sheet():
    assert "O12B Boardroom Goal Sheet architecture installed" in APP_JS
    assert "data-aion-o12b-stage-goal-sheet" in APP_JS
    assert "Stage Goal Sheet" in APP_JS
    assert "stageBoardroomGoalSheet" in APP_JS


def test_o7_bridge_reuses_existing_workflow_canvas_state():
    assert "window.__aionWorkflowGraph = boardGraph" in APP_JS
    assert "window.__aionGoalLoopWorkflowGraph = boardGraph" in APP_JS
    assert "existing_workflow_canvas_reused: true" in APP_JS
    assert "actual_graph_write_performed: true" in APP_JS


def test_o7_bridge_creates_linked_department_sheets_not_second_canvas():
    assert "buildDepartmentGoalSheetGraph" in APP_JS
    assert "window.__aionGoalLoopDepartmentGoalSheets" in APP_JS
    assert "window.__aionGoalLoopLinkedWorkflowRegistry" in APP_JS
    assert "creates_second_canvas: false" in APP_JS
    assert "creates_second_pilot: false" in APP_JS


def test_o7_bridge_exposes_clickable_document_and_link_inspector():
    assert "openGoalSheetInspector" in APP_JS
    assert "data-aion-o12b-open-linked-workflow" in APP_JS
    assert "openLinkedWorkflow" in APP_JS
    assert "meeting_minutes" in APP_JS
    assert "boardroom_decision" in APP_JS
    assert "success_criteria" in APP_JS


def test_o7_bridge_preserves_pilot_handoff_visibility_without_execution():
    assert "Pilot queue preview" in APP_JS
    assert "window.__aionGoalLoopPilotQueuePreview" in APP_JS
    assert "existing_central_pilot_reused: true" in APP_JS
    assert "existing_department_pilots_reused: true" in APP_JS
    assert "execution_allowed_now: false" in APP_JS
    assert "approval_required: true" in APP_JS
