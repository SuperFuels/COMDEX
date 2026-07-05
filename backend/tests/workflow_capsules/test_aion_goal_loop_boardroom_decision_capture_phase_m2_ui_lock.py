from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE M2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE M2 */", start)
    return APP_JS[start:end]


def test_phase_m2_helpers_and_decision_capture_states_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_BOARDROOM_DECISION_CAPTURE_STATES" in block
    assert "function normaliseAionGoalLoopBoardroomDecisionCaptureState" in block
    assert "function buildAionGoalLoopBoardroomDecisionCapture" in block
    assert "function previewAionGoalLoopBoardroomDecisionCapture" in block
    assert "function renderAionGoalLoopBoardroomDecisionCapturePanel" in block

    for state in ["draft", "approved", "rejected", "adjust", "request_more_data", "blocked"]:
        assert state in block


def test_phase_m2_decision_capture_fields_are_locked():
    block = function_block("buildAionGoalLoopBoardroomDecisionCapture")

    for field in [
        "decision_id",
        "package_reference",
        "selected_decision_outcome",
        "decision_state",
        "decision_reason",
        "decision_actor_metadata",
        "approval_gate_reference",
        "evidence_proof_reference",
        "revision_audit_reference",
        "if_approved_route_preview",
        "boardroom_decision_record_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_boardroom_decision_capture.v1" in block


def test_phase_m2_uses_m1_i2_k1_k2_sources():
    block = function_block("buildAionGoalLoopBoardroomDecisionCapture")

    assert "previewAionGoalLoopExecutiveDecisionPackage" in block
    assert "previewAionGoalLoopApprovalGateIntegration" in block
    assert "previewAionGoalLoopEvidenceProofReceipts" in block
    assert "previewAionGoalLoopRevisionHistory" in block
    assert "package_id" in block


def test_phase_m2_if_approved_routes_and_blocking_are_locked():
    block = function_block("buildAionGoalLoopBoardroomDecisionCapture")

    assert "stage_closeout_archive_handoff_preview" in block
    assert "stage_next_goal_loop_action_preview" in block
    assert "return_to_measurement_and_evidence_preview" in block
    assert "return_to_boardroom_adjustment_preview" in block
    assert "resolve_blockers_before_execution_preview" in block
    assert "hold_as_draft_decision_preview" in block
    assert "execution_allowed_now: false" in block
    assert "persistence_allowed_now: false" in block
    assert "archive_allowed_now: false" in block
    assert "external_action_allowed_now: false" in block


def test_phase_m2_renderer_exposes_visible_boardroom_decision_capture_panel():
    block = function_block("renderAionGoalLoopBoardroomDecisionCapturePanel")

    assert 'data-aion-goal-loop-boardroom-decision-capture-panel="true"' in block
    assert 'data-aion-goal-loop-decision-business-container-id="true"' in block
    assert 'data-aion-goal-loop-decision-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-decision-outcome="true"' in block
    assert 'data-aion-goal-loop-decision-safety="true"' in block
    assert 'data-aion-goal-loop-decision-states="true"' in block
    assert 'data-aion-goal-loop-decision-capture-summary="true"' in block
    assert 'data-aion-goal-loop-decision-reason="true"' in block
    assert 'data-aion-goal-loop-decision-actor="true"' in block
    assert 'data-aion-goal-loop-decision-if-approved-route="true"' in block
    assert 'data-aion-goal-loop-decision-preview-boundary="true"' in block


def test_phase_m2_is_preview_only_no_decision_approval_execution_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "boardroom_decision_capture_preview_only: true" in block
    assert "actual_decision_write_performed: false" in block
    assert "actual_approval_write_performed: false" in block
    assert "actual_execution_performed: false" in block
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


def test_phase_m2_is_mounted_after_m1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopExecutiveDecisionPackagePanel()}" in APP_JS
    assert "${renderAionGoalLoopBoardroomDecisionCapturePanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    m1_index = APP_JS.index("${renderAionGoalLoopExecutiveDecisionPackagePanel()}")
    m2_index = APP_JS.index("${renderAionGoalLoopBoardroomDecisionCapturePanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert m1_index < m2_index < cockpit_index
