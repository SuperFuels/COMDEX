from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE E2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE E2 */", start)
    return APP_JS[start:end]


def test_phase_e2_helpers_exist():
    block = phase_block()

    assert "function buildAionGoalLoopManualResultSnapshot" in block
    assert "function previewAionGoalLoopManualResultCapture" in block
    assert "function renderAionGoalLoopManualResultCapturePanel" in block


def test_phase_e2_manual_result_snapshot_fields_are_locked():
    block = function_block("buildAionGoalLoopManualResultSnapshot")

    for field in [
        "result_id",
        "goal_loop_id",
        "goal_id",
        "metric_id",
        "department",
        "source_node_id",
        "metric_name",
        "target",
        "actual",
        "unit",
        "confidence",
        "note",
        "evidence_note",
        "evidence_ids",
        "source",
        "capture_mode",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_manual_result_snapshot.v1" in block
    assert "manual_preview" in block


def test_phase_e2_builds_graph_ledger_and_boardroom_previews():
    block = function_block("previewAionGoalLoopManualResultCapture")

    assert "graph_result_patch_preview" in block
    assert "department_ledger_result_patch_preview" in block
    assert "boardroom_result_preview" in block
    assert "result_node_updates" in block
    assert "manual_results_ready_for_boardroom_preview" in block
    assert "requires_review: true" in block


def test_phase_e2_manual_capture_is_safe_preview_only():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "connector_call_required: false" in block
    assert "ledger_mutation_required: false" in block
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


def test_phase_e2_renderer_exposes_visible_manual_result_capture_panel():
    block = function_block("renderAionGoalLoopManualResultCapturePanel")

    assert 'data-aion-goal-loop-manual-result-capture-panel="true"' in block
    assert 'data-aion-goal-loop-result-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-result-count="true"' in block
    assert 'data-aion-goal-loop-result-department-count="true"' in block
    assert 'data-aion-goal-loop-result-safety="true"' in block
    assert 'data-aion-goal-loop-result-snapshots="true"' in block
    assert 'data-aion-goal-loop-result-preview-boundary="true"' in block
    assert "Evidence placeholder" in block


def test_phase_e2_is_mounted_after_e1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopMeasurementSchemaPanel()}" in APP_JS
    assert "${renderAionGoalLoopManualResultCapturePanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    e1_index = APP_JS.index("${renderAionGoalLoopMeasurementSchemaPanel()}")
    e2_index = APP_JS.index("${renderAionGoalLoopManualResultCapturePanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert e1_index < e2_index < cockpit_index
