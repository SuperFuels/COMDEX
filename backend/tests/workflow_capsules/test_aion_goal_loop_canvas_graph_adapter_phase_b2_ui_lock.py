from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def phase_b1_block() -> str:
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE B1: Contract + Existing Canvas Adapter")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE B1 */", start)
    return APP_JS[start:end]


def test_phase_b2_goal_loop_graph_creates_master_and_department_lanes():
    block = phase_b1_block()

    for node_id in [
        "_minutes",
        "_decision",
        "_board_goal",
        "_agreed_action",
        "_loop_condition",
        "_feedback_to_board",
        "_evidence_receipt",
    ]:
        assert node_id in block

    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'`${{goalLoopId}}_${{department}}_assignment`' in block
        assert f'`${{goalLoopId}}_${{department}}_sub_goal`' in block
        assert f'`${{goalLoopId}}_${{department}}_plan`' in block
        assert f'`${{goalLoopId}}_${{department}}_agent_task`' in block
        assert f'`${{goalLoopId}}_${{department}}_measurement`' in block
        assert f'`${{goalLoopId}}_${{department}}_evaluation`' in block
        assert f'`${{goalLoopId}}_${{department}}_ab_test`' in block


def test_phase_b2_goal_loop_edges_encode_operating_loop():
    block = phase_b1_block()

    expected_conditions = [
        "minutes_to_decision",
        "decision_to_goal",
        "goal_to_actions",
        "action_to_department",
        "assignment_to_sub_goal",
        "sub_goal_to_plan",
        "plan_to_safe_tasks",
        "task_to_measurement",
        "measurement_to_evaluation",
        "evaluation_to_ab_test",
        "evaluation_to_board_feedback",
        "ab_test_loop_back",
        "board_review",
        "goal_complete_with_evidence",
        "adjust_and_continue",
    ]

    for condition in expected_conditions:
        assert condition in block


def test_phase_b2_goal_loop_nodes_are_pilot_and_department_agent_compatible():
    block = phase_b1_block()

    compatible_fields = [
        "id,",
        "node_id: id",
        "type: nodeType",
        "node_type: nodeType",
        "title,",
        "department:",
        "owner_agent:",
        "status,",
        "input_data:",
        "output_data:",
        "metric:",
        "evidence:",
        "approval_required:",
        "next_node_ids:",
        "feedback_target:",
        "receipt_hash:",
        "config,",
        "x,",
        "y,",
    ]

    for field in compatible_fields:
        assert field in block


def test_phase_b2_goal_loop_graph_is_staged_into_existing_workflow_globals():
    block = phase_b1_block()

    assert "window.__aionGoalLoopCanvasContract = contract" in block
    assert "window.__aionGoalLoopWorkflowGraph = graph" in block
    assert "window.__aionWorkflowGraph = graph" in block
    assert "window.__aionWorkflowMainGraph = graph" in block


def test_phase_b2_goal_loop_adapter_does_not_execute_or_persist_yet():
    block = phase_b1_block().lower()

    forbidden = [
        "fetch(",
        "xmlhttprequest",
        "sendbeacon",
        "localstorage.setitem",
        "saveaionworkflowcanvasascapsule(",
        "runaiondepartmentpilotnextsafetask(",
        "approveaiondepartmentpilotplan(",
        "chargecard(",
        "createpayment(",
        "payment_created",
        "payment_confirmed",
        "booking_confirmed",
        "message_sent",
    ]

    for token in forbidden:
        assert token not in block
