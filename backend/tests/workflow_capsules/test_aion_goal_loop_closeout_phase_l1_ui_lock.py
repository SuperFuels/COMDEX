from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE L1: Goal Completion")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE L1 */", start)
    return APP_JS[start:end]


def test_phase_l1_helpers_and_closeout_states_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_CLOSEOUT_STATES" in block
    assert "function buildAionGoalLoopCloseoutSummary" in block
    assert "function previewAionGoalLoopCloseout" in block
    assert "function renderAionGoalLoopCloseoutPanel" in block

    for state in [
        "not_ready",
        "ready_for_boardroom_closeout",
        "blocked_by_open_approvals",
        "blocked_by_open_conflicts",
        "blocked_by_missing_evidence",
        "complete_preview",
    ]:
        assert state in block


def test_phase_l1_closeout_summary_fields_are_locked():
    block = function_block("buildAionGoalLoopCloseoutSummary")

    for field in [
        "goal_completion_state",
        "final_metric_summary",
        "department_contribution_summary",
        "boardroom_final_decision",
        "evidence_proof_receipt_summary",
        "revision_history_summary",
        "blocker_check",
        "completion_readiness_status",
        "archive_handoff_placeholder",
        "next_goal_recommendation_placeholder",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_closeout_summary.v1" in block


def test_phase_l1_uses_k2_k1_i2_h2_evaluation_sources():
    block = function_block("buildAionGoalLoopCloseoutSummary")

    assert "previewAionGoalLoopRevisionHistory" in block
    assert "previewAionGoalLoopEvidenceProofReceipts" in block
    assert "previewAionGoalLoopApprovalGateIntegration" in block
    assert "previewAionGoalLoopCrossFunctionConflictNodes" in block
    assert "previewAionGoalLoopEvaluationEngine" in block


def test_phase_l1_blocker_check_and_archive_handoff_are_locked():
    block = function_block("buildAionGoalLoopCloseoutSummary")

    assert "open_approval_count" in block
    assert "open_conflict_count" in block
    assert "missing_evidence" in block
    assert "blocked_by_open_approvals" in block
    assert "blocked_by_open_conflicts" in block
    assert "blocked_by_missing_evidence" in block
    assert "archive_handoff_placeholder" in block
    assert "archive_execution_allowed: false" in block
    assert "next_goal_recommendation_placeholder" in block


def test_phase_l1_renderer_exposes_visible_closeout_panel():
    block = function_block("renderAionGoalLoopCloseoutPanel")

    assert 'data-aion-goal-loop-closeout-panel="true"' in block
    assert 'data-aion-goal-loop-closeout-business-container-id="true"' in block
    assert 'data-aion-goal-loop-closeout-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-closeout-blocker-count="true"' in block
    assert 'data-aion-goal-loop-closeout-safety="true"' in block
    assert 'data-aion-goal-loop-closeout-states="true"' in block
    assert 'data-aion-goal-loop-closeout-summary="true"' in block
    assert 'data-aion-goal-loop-closeout-departments="true"' in block
    assert 'data-aion-goal-loop-closeout-blockers="true"' in block
    assert 'data-aion-goal-loop-closeout-preview-boundary="true"' in block


def test_phase_l1_is_preview_only_no_completion_archive_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "closeout_preview_only: true" in block
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


def test_phase_l1_closeout_is_mounted_after_k2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopRevisionHistoryPanel()}" in APP_JS
    assert "${renderAionGoalLoopCloseoutPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    k2_index = APP_JS.index("${renderAionGoalLoopRevisionHistoryPanel()}")
    l1_index = APP_JS.index("${renderAionGoalLoopCloseoutPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert k2_index < l1_index < cockpit_index
