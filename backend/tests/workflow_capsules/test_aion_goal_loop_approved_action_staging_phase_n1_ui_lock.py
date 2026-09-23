from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE N1")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE N1 */", start)
    return APP_JS[start:end]


def test_phase_n1_helpers_and_stage_types_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_APPROVED_ACTION_STAGE_TYPES" in block
    assert "function buildAionGoalLoopApprovedActionStage" in block
    assert "function previewAionGoalLoopApprovedActionStaging" in block
    assert "function renderAionGoalLoopApprovedActionStagingPanel" in block

    for stage_type in [
        "closeout_archive_handoff",
        "next_goal_loop_action",
        "measurement_evidence_request",
        "boardroom_adjustment",
        "blocker_resolution",
        "draft_hold",
    ]:
        assert stage_type in block


def test_phase_n1_approved_action_stage_fields_are_locked():
    block = function_block("buildAionGoalLoopApprovedActionStage")

    for field in [
        "stage_id",
        "stage_type",
        "decision_reference",
        "next_action_staging_object",
        "required_approval_check",
        "evidence_proof_carry_forward",
        "revision_audit_carry_forward",
        "business_container_target",
        "execution_plan_preview",
        "if_human_confirms_later_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_approved_action_stage.v1" in block


def test_phase_n1_uses_m2_i2_k1_k2_and_j1_sources():
    block = function_block("buildAionGoalLoopApprovedActionStage")

    assert "previewAionGoalLoopBoardroomDecisionCapture" in block
    assert "previewAionGoalLoopApprovalGateIntegration" in block
    assert "previewAionGoalLoopEvidenceProofReceipts" in block
    assert "previewAionGoalLoopRevisionHistory" in block
    assert "previewAionGoalLoopBusinessContainerPersistence" in block


def test_phase_n1_routes_human_confirmation_and_live_blocking_are_locked():
    block = function_block("buildAionGoalLoopApprovedActionStage")

    assert "stage_closeout_archive_handoff_preview" in block
    assert "stage_next_goal_loop_action_preview" in block
    assert "return_to_measurement_and_evidence_preview" in block
    assert "return_to_boardroom_adjustment_preview" in block
    assert "resolve_blockers_before_execution_preview" in block
    assert "hold_as_draft_decision_preview" in block
    assert "human_confirmation_required: true" in block
    assert "live_execution_blocked: true" in block
    assert "execution_allowed_now: false" in block


def test_phase_n1_renderer_exposes_visible_approved_action_staging_panel():
    block = function_block("renderAionGoalLoopApprovedActionStagingPanel")

    assert 'data-aion-goal-loop-approved-action-staging-panel="true"' in block
    assert 'data-aion-goal-loop-approved-action-business-container-id="true"' in block
    assert 'data-aion-goal-loop-approved-action-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-approved-action-decision-state="true"' in block
    assert 'data-aion-goal-loop-approved-action-safety="true"' in block
    assert 'data-aion-goal-loop-approved-action-stage-types="true"' in block
    assert 'data-aion-goal-loop-approved-action-summary="true"' in block
    assert 'data-aion-goal-loop-approved-action-route="true"' in block
    assert 'data-aion-goal-loop-approved-action-next-stage="true"' in block
    assert 'data-aion-goal-loop-approved-action-execution-plan="true"' in block
    assert 'data-aion-goal-loop-approved-action-preview-boundary="true"' in block


def test_phase_n1_is_preview_only_no_staging_write_execution_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "approved_action_staging_preview_only: true" in block
    assert "actual_stage_write_performed: false" in block
    assert "actual_execution_performed: false" in block
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


def test_phase_n1_is_mounted_after_m2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopBoardroomDecisionCapturePanel()}" in APP_JS
    assert "${renderAionGoalLoopApprovedActionStagingPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    m2_index = APP_JS.index("${renderAionGoalLoopBoardroomDecisionCapturePanel()}")
    n1_index = APP_JS.index("${renderAionGoalLoopApprovedActionStagingPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert m2_index < n1_index < cockpit_index
