from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE F2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE F2 */", start)
    return APP_JS[start:end]


def test_phase_f2_helpers_exist():
    block = phase_block()

    assert "function buildAionGoalLoopAbTestProposalFromEvaluation" in block
    assert "function previewAionGoalLoopGeneratedAbTestsFromEvaluation" in block
    assert "function renderAionGoalLoopGeneratedAbTestPanel" in block


def test_phase_f2_proposal_links_to_source_evaluation_goal_and_department():
    block = function_block("buildAionGoalLoopAbTestProposalFromEvaluation")

    for field in [
        "source_evaluation_id",
        "source_metric_id",
        "goal_loop_id",
        "goal_id",
        "department",
        "source_status",
        "source_next_action",
    ]:
        assert field in block

    assert "aion.goal_loop_ab_test_generated_from_evaluation.v1" in block


def test_phase_f2_generates_variants_and_approval_requirement():
    block = function_block("buildAionGoalLoopAbTestProposalFromEvaluation")

    assert "variant_a" in block
    assert "variant_b" in block
    assert "Current approach" in block
    assert "Recommended improvement" in block
    assert "approval_requirement" in block
    assert "awaiting_board_approval" in block
    assert "boardroom_review_item" in block
    assert "generated_ab_test_proposal" in block


def test_phase_f2_preview_builds_from_evaluation_candidates():
    block = function_block("previewAionGoalLoopGeneratedAbTestsFromEvaluation")

    assert "buildAionGoalLoopEvaluationPreview" in block
    assert "next_action === \"propose_ab_test\"" in block
    assert "status === \"off_track\"" in block
    assert "buildAionGoalLoopAbTestProposalFromEvaluation" in block
    assert "generated_ab_test_proposals" in block
    assert "boardroom_review_items" in block
    assert "graph_patch_preview" in block
    assert "node_additions" in block
    assert "edge_additions" in block


def test_phase_f2_renderer_exposes_visible_generated_ab_test_panel():
    block = function_block("renderAionGoalLoopGeneratedAbTestPanel")

    assert 'data-aion-goal-loop-generated-ab-test-panel="true"' in block
    assert 'data-aion-goal-loop-generated-ab-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-generated-ab-candidate-count="true"' in block
    assert 'data-aion-goal-loop-generated-ab-count="true"' in block
    assert 'data-aion-goal-loop-generated-ab-safety="true"' in block
    assert 'data-aion-goal-loop-generated-ab-proposals="true"' in block
    assert 'data-aion-goal-loop-generated-ab-variant-a="true"' in block
    assert 'data-aion-goal-loop-generated-ab-variant-b="true"' in block
    assert 'data-aion-goal-loop-generated-ab-preview-boundary="true"' in block


def test_phase_f2_is_preview_only_safe_boundary():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "approval_required: true" in block
    assert "campaign_launch_required: false" in block
    assert "connector_call_required: false" in block
    assert "execution_blocked: true" in block
    assert "persistence_required: false" in block
    assert "external_side_effects: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block

    assert "fetch(" not in forbidden
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden
    assert "campaign_launch_required: true" not in forbidden
    assert "payment_created: true" not in forbidden
    assert "booking_created: true" not in forbidden


def test_phase_f2_is_mounted_after_f1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopAbTestPanel()}" in APP_JS
    assert "${renderAionGoalLoopGeneratedAbTestPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    f1_index = APP_JS.index("${renderAionGoalLoopAbTestPanel()}")
    f2_index = APP_JS.index("${renderAionGoalLoopGeneratedAbTestPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert f1_index < f2_index < cockpit_index
