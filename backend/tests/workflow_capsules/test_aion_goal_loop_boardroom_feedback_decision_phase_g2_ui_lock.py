from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE G2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE G2 */", start)
    return APP_JS[start:end]


def test_phase_g2_helpers_and_actions_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_BOARDROOM_FEEDBACK_DECISIONS" in block
    assert "function normaliseAionGoalLoopBoardroomFeedbackDecision" in block
    assert "function buildAionGoalLoopBoardroomFeedbackDecision" in block
    assert "function previewAionGoalLoopBoardroomFeedbackDecision" in block
    assert "function renderAionGoalLoopBoardroomFeedbackDecisionPanel" in block

    for action in ["accept", "reject", "adjust", "request_more_data"]:
      assert action in block


def test_phase_g2_decision_object_fields_are_locked():
    block = function_block("buildAionGoalLoopBoardroomFeedbackDecision")

    for field in [
        "decision_id",
        "node_type",
        "board_adjustment",
        "goal_loop_id",
        "goal_id",
        "feedback_id",
        "department",
        "decision",
        "decision_label",
        "continuation_path",
        "adjustment_summary",
        "requested_data",
        "boardroom_action_preview",
        "graph_patch_preview",
        "audit_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_boardroom_feedback_decision.v1" in block


def test_phase_g2_graph_patch_and_audit_are_preview_safe():
    block = function_block("buildAionGoalLoopBoardroomFeedbackDecision")

    assert "update_feedback_node" in block
    assert "add_or_update_node" in block
    assert "board_decides_feedback" in block
    assert "graph_mutation_required: false" in block
    assert "aion.goal_loop_boardroom_decision_audit_preview.v1" in block
    assert "receipt_required_on_persistence" in block
    assert "provenance_required: true" in block


def test_phase_g2_preview_builds_decisions_from_feedback_nodes():
    block = function_block("previewAionGoalLoopBoardroomFeedbackDecision")

    assert "previewAionGoalLoopFeedbackToBoard" in block
    assert "feedback_nodes" in block
    assert "buildAionGoalLoopBoardroomFeedbackDecision" in block
    assert "allowed_actions" in block
    assert "decisions" in block
    assert "board_adjustment_nodes" in block
    assert "feedback_updates" in block
    assert "audit_previews" in block


def test_phase_g2_renderer_exposes_visible_boardroom_decision_panel():
    block = function_block("renderAionGoalLoopBoardroomFeedbackDecisionPanel")

    assert 'data-aion-goal-loop-boardroom-feedback-decision-panel="true"' in block
    assert 'data-aion-goal-loop-boardroom-decision-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-boardroom-decision-feedback-count="true"' in block
    assert 'data-aion-goal-loop-boardroom-decision-count="true"' in block
    assert 'data-aion-goal-loop-boardroom-decision-safety="true"' in block
    assert 'data-aion-goal-loop-boardroom-decision-actions="true"' in block
    assert 'data-aion-goal-loop-boardroom-decision-items="true"' in block
    assert 'data-aion-goal-loop-boardroom-decision-preview-boundary="true"' in block


def test_phase_g2_is_preview_only_safe_boundary():
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


def test_phase_g2_is_mounted_after_g1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopFeedbackToBoardPanel()}" in APP_JS
    assert "${renderAionGoalLoopBoardroomFeedbackDecisionPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    g1_index = APP_JS.index("${renderAionGoalLoopFeedbackToBoardPanel()}")
    g2_index = APP_JS.index("${renderAionGoalLoopBoardroomFeedbackDecisionPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert g1_index < g2_index < cockpit_index
