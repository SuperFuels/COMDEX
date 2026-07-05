from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE G1")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE G1 */", start)
    return APP_JS[start:end]


def test_phase_g1_helpers_exist():
    block = phase_block()

    assert "function buildAionGoalLoopFeedbackToBoardNode" in block
    assert "function previewAionGoalLoopFeedbackToBoard" in block
    assert "function renderAionGoalLoopFeedbackToBoardPanel" in block


def test_phase_g1_feedback_node_fields_are_locked():
    block = function_block("buildAionGoalLoopFeedbackToBoardNode")

    for field in [
        "feedback_id",
        "node_type",
        "feedback_to_board",
        "goal_loop_id",
        "goal_id",
        "department",
        "department_status",
        "metrics",
        "risks",
        "evidence_ids",
        "recommendation",
        "required_board_decision",
        "boardroom_review_item",
        "graph_patch_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_feedback_to_board.v1" in block


def test_phase_g1_feedback_includes_boardroom_review_item_and_graph_patch():
    block = function_block("buildAionGoalLoopFeedbackToBoardNode")

    assert "department_feedback_to_board" in block
    assert "needs_board_decision" in block
    assert "required_decision" in block
    assert "add_or_update_node" in block
    assert "reports_feedback_to_board" in block
    assert "included_in_board_feedback" in block
    assert "graph_mutation_required: false" in block


def test_phase_g1_preview_builds_feedback_for_departments():
    block = function_block("previewAionGoalLoopFeedbackToBoard")

    assert "buildAionGoalLoopEvaluationPreview" in block
    assert "buildAionGoalLoopFeedbackToBoardNode" in block
    assert "feedback_nodes" in block
    assert "boardroom_review_items" in block
    assert "node_updates" in block
    assert "edge_additions" in block
    assert "marketing" in block
    assert "sales" in block
    assert "finance" in block
    assert "operations" in block
    assert "support" in block


def test_phase_g1_renderer_exposes_visible_feedback_panel():
    block = function_block("renderAionGoalLoopFeedbackToBoardPanel")

    assert 'data-aion-goal-loop-feedback-to-board-panel="true"' in block
    assert 'data-aion-goal-loop-feedback-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-feedback-department-count="true"' in block
    assert 'data-aion-goal-loop-feedback-count="true"' in block
    assert 'data-aion-goal-loop-feedback-safety="true"' in block
    assert 'data-aion-goal-loop-feedback-nodes="true"' in block
    assert 'data-aion-goal-loop-feedback-preview-boundary="true"' in block


def test_phase_g1_is_preview_only_safe_boundary():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "graph_mutation_required: false" in block
    assert "persistence_required: false" in block
    assert "execution_blocked: true" in block
    assert "external_side_effects: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block

    assert "fetch(" not in forbidden
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden
    assert "payment_created: true" not in forbidden
    assert "booking_created: true" not in forbidden


def test_phase_g1_is_mounted_after_f2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopGeneratedAbTestPanel()}" in APP_JS
    assert "${renderAionGoalLoopFeedbackToBoardPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    f2_index = APP_JS.index("${renderAionGoalLoopGeneratedAbTestPanel()}")
    g1_index = APP_JS.index("${renderAionGoalLoopFeedbackToBoardPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert f2_index < g1_index < cockpit_index
