from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def phase_b1_block() -> str:
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE B1: Contract + Existing Canvas Adapter")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE B1 */", start)
    return APP_JS[start:end]


def test_goal_loop_contract_helpers_exist_without_new_canvas_or_new_pilot():
    block = phase_b1_block()

    assert "AION_GOAL_LOOP_CANVAS_SCHEMA_VERSION" in block
    assert "AION_GOAL_LOOP_NODE_TYPES" in block
    assert "AION_GOAL_LOOP_STORAGE_KEYS" in block
    assert "function normaliseAionGoalLoopDepartmentKey" in block
    assert "function buildAionGoalLoopCanvasContract" in block
    assert "function buildAionGoalLoopWorkflowGraph" in block
    assert "function createAionGoalLoopCanvasFromBoardGoal" in block

    assert "function render" not in block
    assert "new Pilot" not in block
    assert "new canvas" not in block


def test_goal_loop_contract_contains_required_fields():
    block = phase_b1_block()

    required_fields = [
        "goal_loop_id",
        "business_id",
        "workspace_id",
        "source_board_meeting_id",
        "source_minutes_id",
        "board_goal",
        "department_goal_map",
        "canvas_graph",
        "execution_policy",
        "measurement_plan",
        "feedback_policy",
        "approval_policy",
        "evidence_links",
        "receipt_hash",
        "status",
        "created_at",
        "updated_at",
    ]

    for field in required_fields:
        assert field in block


def test_goal_loop_node_types_registered_for_existing_workflow_graph():
    block = phase_b1_block()

    node_types = [
        "board_meeting_minutes",
        "board_decision",
        "board_goal",
        "agreed_action",
        "department_assignment",
        "department_sub_goal",
        "department_plan",
        "agent_task",
        "measurement_plan",
        "execution_result",
        "evaluation",
        "ab_test",
        "improvement_proposal",
        "feedback_to_board",
        "board_adjustment",
        "loop_condition",
        "evidence_receipt",
    ]

    for node_type in node_types:
        assert f'"{node_type}"' in block


def test_goal_loop_graph_uses_existing_workflow_canvas_shape():
    block = phase_b1_block()

    assert "schema_version: \"aion.workflow_goal_loop_graph.v1\"" in block
    assert "canvas_type: \"goal_loop\"" in block
    assert "workflow_id:" in block
    assert "business_container:" in block
    assert "nodes:" in block
    assert "edges:" in block
    assert "compiled_glyph: null" in block
    assert "window.__aionWorkflowGraph" in block
    assert "window.__aionWorkflowMainGraph" in block


def test_goal_loop_contract_is_generic_and_preview_safe():
    block = phase_b1_block().lower()

    assert "home_fixed" not in block
    assert "home fixed" not in block
    assert "costa-conexion" not in block
    assert "costa_conexion" not in block

    assert "preview_only_default: true" in block
    assert "approval_required_for_external_actions: true" in block
    assert "payment_actions_blocked_without_exact_approval: true" in block
    assert "booking_actions_blocked_without_exact_approval: true" in block
    assert "customer_messages_blocked_without_policy_approval: true" in block

    assert "fetch(" not in block
    assert "xmlhttprequest" not in block
    assert "sendbeacon" not in block
