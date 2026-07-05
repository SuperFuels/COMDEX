from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o8_entrypoint_now_routes_to_o12b_goal_sheet_architecture():
    assert "BEGIN AION O12B BOARDROOM GOAL SHEET ARCHITECTURE" in APP_JS
    assert "window.aionStageNativeGoalLoopWorkflowO8 = stageBoardroomGoalSheet" in APP_JS
    assert "window.aionStageBoardroomGoalSheetO12B = stageBoardroomGoalSheet" in APP_JS


def test_o8_no_longer_dumps_full_department_goal_loop_onto_one_canvas():
    assert "RETIRED BY O12B" in APP_JS
    assert "Boardroom Goal Sheet" in APP_JS
    assert "department_goal_sheets" in APP_JS
    assert "Linked department sheets" in APP_JS
    assert "Department goal sheets are linked records, not dumped into the Boardroom canvas." in APP_JS


def test_o8_still_writes_to_real_workflow_graph_state_not_overlay_layer():
    assert "window.__aionWorkflowGraph = boardGraph" in APP_JS
    assert "window.__aionGoalLoopWorkflowGraph = boardGraph" in APP_JS
    assert "used_existing_canvas: true" in APP_JS
    assert "creates_second_canvas: false" in APP_JS
    assert "creates_second_pilot: false" in APP_JS


def test_o8_goal_sheet_preserves_preview_safety_contract():
    assert "preview_only: true" in APP_JS
    assert "connector_call_required: false" in APP_JS
    assert "external_side_effects: false" in APP_JS
    assert "booking_created: false" in APP_JS
    assert "payment_created: false" in APP_JS
    assert "customer_message_sent: false" in APP_JS
    assert "no_live_execution: true" in APP_JS
    assert "no_connector_calls: true" in APP_JS


def test_o8_goal_sheet_has_real_boardroom_documents_and_pilot_handoff():
    assert "Board meeting minutes" in APP_JS
    assert "Board decision" in APP_JS
    assert "Actual goal" in APP_JS
    assert "Success criteria" in APP_JS
    assert "Pilot queue preview" in APP_JS
    assert "Evidence feedback" in APP_JS
