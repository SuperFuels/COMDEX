from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def goal_loop_block() -> str:
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE B1: Contract + Existing Canvas Adapter")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE B1 */", start)
    return APP_JS[start:end]


def test_phase_c1_boardroom_goal_loop_helpers_exist():
    block = goal_loop_block()

    assert "function buildAionBoardroomGoalLoopInputFromDecision" in block
    assert "function stageAionBoardroomDecisionGoalLoopIntoWorkflowCanvas" in block
    assert "window.buildAionBoardroomGoalLoopInputFromDecision = buildAionBoardroomGoalLoopInputFromDecision" in block
    assert "window.stageAionBoardroomDecisionGoalLoopIntoWorkflowCanvas = stageAionBoardroomDecisionGoalLoopIntoWorkflowCanvas" in block


def test_phase_c1_boardroom_input_maps_decision_to_goal_contract_fields():
    block = goal_loop_block()

    required = [
        "source_board_meeting_id",
        "source_minutes_id",
        "board_goal",
        "department_goal_map",
        "target_metric",
        "target_value",
        "timeframe",
        "business_id",
        "workspace_id",
    ]

    for token in required:
        assert token in block


def test_phase_c1_boardroom_department_mapping_uses_all_core_departments():
    block = goal_loop_block()

    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'department: "{department}"' in block
        assert f'owner_agent: "{department}_pilot"' in block


def test_phase_c1_boardroom_stages_existing_canvas_only():
    block = goal_loop_block()

    assert "stageAionGoalLoopCanvasIntoExistingWorkflowCanvas(input" in block
    assert 'focus_reason: "boardroom_decision_goal_loop"' in block

    forbidden = [
        "fetch(",
        "XMLHttpRequest",
        "sendBeacon",
        "localStorage.setItem",
        "saveAionWorkflowCanvasAsCapsule(",
        "runAionDepartmentPilotNextSafeTask(",
        "approveAionDepartmentPilotPlan(",
        "chargeCard(",
        "createPayment(",
        "payment_created",
        "booking_confirmed",
        "message_sent",
    ]

    for token in forbidden:
        assert token not in block


def test_phase_c1_boardroom_goal_loop_is_generic():
    block = goal_loop_block().lower()

    assert "home_fixed" not in block
    assert "home fixed" not in block
    assert "costa-conexion" not in block
    assert "costa_conexion" not in block
