from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE F1")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE F1 */", start)
    return APP_JS[start:end]


def test_phase_f1_helpers_exist():
    block = phase_block()

    assert "function buildAionGoalLoopAbTestNode" in block
    assert "function buildAionGoalLoopAbTestLifecyclePreview" in block
    assert "function renderAionGoalLoopAbTestPanel" in block


def test_phase_f1_lifecycle_statuses_are_locked():
    block = phase_block()

    for status in [
        "proposed",
        "approved",
        "running",
        "measuring",
        "evaluated",
        "winner_selected",
        "next_test_proposed",
        "complete",
    ]:
        assert status in block


def test_phase_f1_ab_test_node_fields_are_locked():
    block = function_block("buildAionGoalLoopAbTestNode")

    for field in [
        "node_type",
        "ab_test",
        "variant_a",
        "variant_b",
        "hypothesis",
        "success_metric",
        "test_duration",
        "approval_state",
        "result_capture_placeholder",
        "winner_decision_placeholder",
        "next_variant_proposal_placeholder",
        "boardroom_ab_summary",
        "source_evaluation_id",
    ]:
        assert field in block

    assert "aion.goal_loop_ab_test_node.v1" in block


def test_phase_f1_lifecycle_preview_links_from_evaluation_and_boardroom():
    block = function_block("buildAionGoalLoopAbTestLifecyclePreview")

    assert "buildAionGoalLoopEvaluationPreview" in block
    assert "propose_ab_test" in block
    assert "off_track" in block
    assert "ab_test_nodes" in block
    assert "boardroom_ab_summary" in block
    assert "graph_ab_test_patch_preview" in block
    assert "ab_test_node_additions" in block
    assert "required_board_review" in block


def test_phase_f1_renderer_exposes_visible_ab_test_panel():
    block = function_block("renderAionGoalLoopAbTestPanel")

    assert 'data-aion-goal-loop-ab-test-panel="true"' in block
    assert 'data-aion-goal-loop-ab-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-ab-count="true"' in block
    assert 'data-aion-goal-loop-ab-lifecycle-count="true"' in block
    assert 'data-aion-goal-loop-ab-safety="true"' in block
    assert 'data-aion-goal-loop-ab-lifecycle="true"' in block
    assert 'data-aion-goal-loop-ab-nodes="true"' in block
    assert 'data-aion-goal-loop-ab-variant-a="true"' in block
    assert 'data-aion-goal-loop-ab-variant-b="true"' in block
    assert 'data-aion-goal-loop-ab-preview-boundary="true"' in block


def test_phase_f1_is_preview_only_safe_boundary():
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


def test_phase_f1_is_mounted_after_e3_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopEvaluationEnginePanel()}" in APP_JS
    assert "${renderAionGoalLoopAbTestPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    e3_index = APP_JS.index("${renderAionGoalLoopEvaluationEnginePanel()}")
    f1_index = APP_JS.index("${renderAionGoalLoopAbTestPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert e3_index < f1_index < cockpit_index
