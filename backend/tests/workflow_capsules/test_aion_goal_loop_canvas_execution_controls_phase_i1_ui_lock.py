from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE I1")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE I1 */", start)
    return APP_JS[start:end]


def test_phase_i1_helpers_and_controls_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_CANVAS_EXECUTION_CONTROLS" in block
    assert "function buildAionGoalLoopCanvasExecutionControl" in block
    assert "function previewAionGoalLoopCanvasExecutionControls" in block
    assert "function renderAionGoalLoopCanvasExecutionControlsPanel" in block

    for control in [
        "generate_department_canvases",
        "stage_agent_tasks",
        "request_approval",
        "start_safe_execution",
        "record_result",
        "evaluate_result",
        "generate_ab_test",
        "send_feedback_to_boardroom",
        "mark_goal_complete",
        "pause_loop",
        "archive_loop",
    ]:
        assert control in block


def test_phase_i1_control_object_fields_are_locked():
    block = function_block("buildAionGoalLoopCanvasExecutionControl")

    for field in [
        "control_id",
        "label",
        "goal_loop_id",
        "target",
        "required_surface",
        "action_state",
        "approval_required",
        "execution_allowed",
        "route",
        "graph_patch_preview",
        "audit_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_canvas_execution_control.v1" in block


def test_phase_i1_reuses_existing_surfaces_and_blocks_second_canvas_pilot():
    block = phase_block()

    assert "uses_existing_workflow_canvas: true" in block
    assert "central_pilot_reused: true" in block
    assert "department_pilots_reused: true" in block
    assert "workflow_canvas_reused: true" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block


def test_phase_i1_approval_sensitive_controls_are_blocked():
    block = function_block("buildAionGoalLoopCanvasExecutionControl")

    assert 'controlId === "start_safe_execution"' in block
    assert 'controlId === "request_approval"' in block
    assert 'controlId === "archive_loop"' in block
    assert "blocked_until_approval" in block
    assert "execution_allowed: false" in block


def test_phase_i1_renderer_exposes_visible_controls_panel():
    block = function_block("renderAionGoalLoopCanvasExecutionControlsPanel")

    assert 'data-aion-goal-loop-canvas-execution-controls-panel="true"' in block
    assert 'data-aion-goal-loop-controls-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-controls-count="true"' in block
    assert 'data-aion-goal-loop-controls-blocked-count="true"' in block
    assert 'data-aion-goal-loop-controls-safety="true"' in block
    assert 'data-aion-goal-loop-controls-list="true"' in block
    assert 'data-aion-goal-loop-controls-preview-boundary="true"' in block


def test_phase_i1_is_preview_staging_only_safe_boundary():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "staging_only: true" in block
    assert "graph_mutation_required: false" in block
    assert "persistence_required: false" in block
    assert "execution_blocked: true" in block
    assert "external_side_effects: false" in block
    assert "connector_call_required: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block

    assert "fetch(" not in forbidden
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden
    assert "payment_created: true" not in forbidden
    assert "booking_created: true" not in forbidden


def test_phase_i1_is_mounted_after_h2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopCrossFunctionConflictPanel()}" in APP_JS
    assert "${renderAionGoalLoopCanvasExecutionControlsPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    h2_index = APP_JS.index("${renderAionGoalLoopCrossFunctionConflictPanel()}")
    i1_index = APP_JS.index("${renderAionGoalLoopCanvasExecutionControlsPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert h2_index < i1_index < cockpit_index
