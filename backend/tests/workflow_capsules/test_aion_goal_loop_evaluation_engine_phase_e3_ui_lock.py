from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE E3")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE E3 */", start)
    return APP_JS[start:end]


def test_phase_e3_helpers_exist():
    block = phase_block()

    assert "function evaluateAionGoalLoopMetricResult" in block
    assert "function buildAionGoalLoopEvaluationPreview" in block
    assert "function renderAionGoalLoopEvaluationEnginePanel" in block


def test_phase_e3_statuses_and_next_actions_are_locked():
    block = phase_block()

    for status in ["on_track", "off_track", "blocked", "unknown", "complete"]:
        assert status in block

    for action in [
        "continue_loop",
        "propose_ab_test",
        "pause_loop",
        "mark_complete",
        "request_more_data",
    ]:
        assert action in block


def test_phase_e3_metric_evaluation_output_fields_are_locked():
    block = function_block("evaluateAionGoalLoopMetricResult")

    for field in [
        "status",
        "reason",
        "recommendation",
        "next_action",
        "confidence",
        "department",
        "metric_id",
        "goal_id",
        "evidence_ids",
        "target",
        "actual",
        "unit",
    ]:
        assert field in block

    assert "Number(targetRaw)" in block
    assert "Number(actualRaw)" in block
    assert "lowerIsBetter" in block


def test_phase_e3_builds_evaluation_preview_and_boardroom_summary():
    block = function_block("buildAionGoalLoopEvaluationPreview")

    assert "previewAionGoalLoopManualResultCapture" in block
    assert "evaluateAionGoalLoopMetricResult" in block
    assert "aion.goal_loop_evaluation.v1" in block
    assert "boardroom_evaluation_summary" in block
    assert "graph_evaluation_patch_preview" in block
    assert "evaluation_node_updates" in block
    assert "recommended_board_action" in block


def test_phase_e3_renderer_exposes_visible_evaluation_panel():
    block = function_block("renderAionGoalLoopEvaluationEnginePanel")

    assert 'data-aion-goal-loop-evaluation-engine-panel="true"' in block
    assert 'data-aion-goal-loop-evaluation-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-evaluation-count="true"' in block
    assert 'data-aion-goal-loop-evaluation-board-action="true"' in block
    assert 'data-aion-goal-loop-evaluation-safety="true"' in block
    assert 'data-aion-goal-loop-evaluations="true"' in block
    assert 'data-aion-goal-loop-evaluation-preview-boundary="true"' in block


def test_phase_e3_is_preview_only_safe_boundary():
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
    assert "updateaiondepartmentintelligence(" not in forbidden
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden
    assert "payment_created: true" not in forbidden
    assert "booking_created: true" not in forbidden


def test_phase_e3_is_mounted_after_e2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopManualResultCapturePanel()}" in APP_JS
    assert "${renderAionGoalLoopEvaluationEnginePanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    e2_index = APP_JS.index("${renderAionGoalLoopManualResultCapturePanel()}")
    e3_index = APP_JS.index("${renderAionGoalLoopEvaluationEnginePanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert e2_index < e3_index < cockpit_index
