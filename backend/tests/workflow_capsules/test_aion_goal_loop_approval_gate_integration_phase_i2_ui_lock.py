from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE I2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE I2 */", start)
    return APP_JS[start:end]


def test_phase_i2_helpers_actions_and_states_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_APPROVAL_ACTION_TYPES" in block
    assert "AION_GOAL_LOOP_APPROVAL_STATES" in block
    assert "function normaliseAionGoalLoopApprovalActionType" in block
    assert "function buildAionGoalLoopApprovalGateRequest" in block
    assert "function previewAionGoalLoopApprovalGateIntegration" in block
    assert "function renderAionGoalLoopApprovalGatePanel" in block

    for action_type in [
        "external_message",
        "booking_confirmation",
        "payment_action",
        "connector_write",
        "safe_internal_execution",
        "archive_loop",
    ]:
        assert action_type in block

    for state in ["not_required", "required", "requested", "approved", "rejected", "blocked"]:
        assert state in block


def test_phase_i2_approval_request_fields_are_locked():
    block = function_block("buildAionGoalLoopApprovalGateRequest")

    for field in [
        "approval_id",
        "goal_loop_id",
        "source_id",
        "source_type",
        "department",
        "action_type",
        "approval_state",
        "approval_required",
        "exact_approval_required",
        "execution_allowed",
        "approval_policy",
        "graph_node_approval_patch_preview",
        "task_queue_approval_patch_preview",
        "boardroom_approval_preview",
        "audit_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_approval_gate_request.v1" in block


def test_phase_i2_exact_approval_policy_is_locked():
    block = function_block("buildAionGoalLoopApprovalGateRequest")

    assert "no_external_live_action_without_explicit_approval" in block
    assert "no_payment_without_exact_approval" in block
    assert "no_booking_without_exact_approval" in block
    assert "no_customer_message_without_policy_approval" in block
    assert "provenance_required" in block
    assert "evidence_or_confidence_required" in block
    assert "boardroom_decision_auditable" in block
    assert "execution_allowed: false" in block


def test_phase_i2_preview_links_controls_to_graph_task_queue_and_boardroom():
    block = function_block("previewAionGoalLoopApprovalGateIntegration")

    assert "previewAionGoalLoopCanvasExecutionControls" in block
    assert "buildAionGoalLoopApprovalGateRequest" in block
    assert "approval_requests" in block
    assert "boardroom_approval_previews" in block
    assert "node_approval_updates" in block
    assert "task_queue_approval_updates" in block
    assert "audit_previews" in block
    assert "safety_policy" in block


def test_phase_i2_renderer_exposes_visible_approval_gate_panel():
    block = function_block("renderAionGoalLoopApprovalGatePanel")

    assert 'data-aion-goal-loop-approval-gate-panel="true"' in block
    assert 'data-aion-goal-loop-approval-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-approval-request-count="true"' in block
    assert 'data-aion-goal-loop-approval-required-count="true"' in block
    assert 'data-aion-goal-loop-exact-approval-count="true"' in block
    assert 'data-aion-goal-loop-approval-requests="true"' in block
    assert 'data-aion-goal-loop-approval-preview-boundary="true"' in block


def test_phase_i2_is_preview_only_and_blocks_execution():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "graph_mutation_required: false" in block
    assert "queue_mutation_required: false" in block
    assert "persistence_required: false" in block
    assert "execution_blocked: true" in block
    assert "external_side_effects: false" in block
    assert "connector_call_required: false" in block
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


def test_phase_i2_is_mounted_after_i1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopCanvasExecutionControlsPanel()}" in APP_JS
    assert "${renderAionGoalLoopApprovalGatePanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    i1_index = APP_JS.index("${renderAionGoalLoopCanvasExecutionControlsPanel()}")
    i2_index = APP_JS.index("${renderAionGoalLoopApprovalGatePanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert i1_index < i2_index < cockpit_index
