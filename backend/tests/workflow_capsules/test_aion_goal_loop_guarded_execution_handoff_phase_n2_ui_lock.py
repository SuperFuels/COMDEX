from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE N2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE N2 */", start)
    return APP_JS[start:end]


def test_phase_n2_helpers_and_handoff_states_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_GUARDED_EXECUTION_HANDOFF_STATES" in block
    assert "function buildAionGoalLoopGuardedExecutionHandoff" in block
    assert "function previewAionGoalLoopGuardedExecutionHandoff" in block
    assert "function renderAionGoalLoopGuardedExecutionHandoffPanel" in block

    for state in [
        "not_ready",
        "blocked_waiting_human_confirmation",
        "blocked_waiting_approval_recheck",
        "blocked_waiting_evidence_recheck",
        "ready_for_future_guarded_execution_phase",
        "held_as_preview",
    ]:
        assert state in block


def test_phase_n2_guarded_execution_handoff_fields_are_locked():
    block = function_block("buildAionGoalLoopGuardedExecutionHandoff")

    for field in [
        "handoff_id",
        "approved_action_stage_reference",
        "boardroom_decision_reference",
        "guard_envelope_preview",
        "execution_queue_item_preview",
        "approval_gate_recheck",
        "evidence_proof_recheck",
        "revision_audit_recheck",
        "replay_restore_reference",
        "connector_permission_matrix_preview",
        "side_effect_preflight",
        "if_all_guards_pass_later_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_guarded_execution_handoff.v1" in block


def test_phase_n2_uses_n1_m2_i2_k1_k2_and_j2_sources():
    block = function_block("buildAionGoalLoopGuardedExecutionHandoff")

    assert "previewAionGoalLoopApprovedActionStaging" in block
    assert "previewAionGoalLoopBoardroomDecisionCapture" in block
    assert "previewAionGoalLoopApprovalGateIntegration" in block
    assert "previewAionGoalLoopEvidenceProofReceipts" in block
    assert "previewAionGoalLoopRevisionHistory" in block
    assert "previewAionGoalLoopReplayRestore" in block


def test_phase_n2_guard_envelope_queue_and_connector_matrix_are_locked():
    block = function_block("buildAionGoalLoopGuardedExecutionHandoff")

    assert "guard_envelope_preview" in block
    assert "human_confirmation_required: true" in block
    assert "approval_recheck_required: true" in block
    assert "evidence_recheck_required: true" in block
    assert "execution_queue_item_preview" in block
    assert "queue_state: \"not_enqueued_preview\"" in block
    assert "connector_permission_matrix_preview" in block
    assert "connector_calls_allowed_now: false" in block
    assert "email_allowed_now: false" in block
    assert "payment_allowed_now: false" in block
    assert "booking_allowed_now: false" in block


def test_phase_n2_renderer_exposes_visible_guarded_execution_handoff_panel():
    block = function_block("renderAionGoalLoopGuardedExecutionHandoffPanel")

    assert 'data-aion-goal-loop-guarded-execution-handoff-panel="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-business-container-id="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-queue-state="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-safety="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-states="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-summary="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-guard-envelope="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-queue-item="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-connectors="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-next-live-phase="true"' in block
    assert 'data-aion-goal-loop-guarded-handoff-preview-boundary="true"' in block


def test_phase_n2_is_preview_only_no_handoff_queue_execution_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "guarded_execution_handoff_preview_only: true" in block
    assert "actual_handoff_write_performed: false" in block
    assert "actual_queue_write_performed: false" in block
    assert "actual_execution_performed: false" in block
    assert "actual_connector_call_performed: false" in block
    assert "actual_approval_write_performed: false" in block
    assert "actual_completion_write_performed: false" in block
    assert "actual_archive_performed: false" in block
    assert "actual_container_write_performed: false" in block
    assert "graph_mutation_required: false" in block
    assert "persistence_required: false" in block
    assert "external_side_effects: false" in block
    assert "connector_call_required: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block

    assert "fetch(" not in forbidden
    assert "apiGet" not in block
    assert "apiPost(" not in block
    assert "writeFile" not in block
    assert "localStorage.setItem" not in block
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden


def test_phase_n2_is_mounted_after_n1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopApprovedActionStagingPanel()}" in APP_JS
    assert "${renderAionGoalLoopGuardedExecutionHandoffPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    n1_index = APP_JS.index("${renderAionGoalLoopApprovedActionStagingPanel()}")
    n2_index = APP_JS.index("${renderAionGoalLoopGuardedExecutionHandoffPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert n1_index < n2_index < cockpit_index
