from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE L2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE L2 */", start)
    return APP_JS[start:end]


def test_phase_l2_helpers_and_dashboard_status_fields_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_DASHBOARD_STATUS_FIELDS" in block
    assert "function buildAionGoalLoopDashboardSummary" in block
    assert "function previewAionGoalLoopDashboardSummary" in block
    assert "function renderAionGoalLoopDashboardSummaryPanel" in block

    for field in [
        "current_goal_loop_state",
        "department_progress",
        "task_queue_status",
        "approval_status",
        "conflict_status",
        "evidence_proof_status",
        "revision_audit_status",
        "closeout_readiness",
        "next_recommended_action",
        "overall_safety_status",
    ]:
        assert field in block


def test_phase_l2_dashboard_summary_fields_are_locked():
    block = function_block("buildAionGoalLoopDashboardSummary")

    for field in [
        "current_goal_loop_state",
        "department_progress",
        "task_queue_status",
        "approval_status",
        "conflict_status",
        "evidence_proof_status",
        "revision_audit_status",
        "closeout_readiness",
        "next_recommended_action",
        "overall_safety_status",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_dashboard_summary.v1" in block


def test_phase_l2_uses_l1_k2_k1_i2_h2_and_controls_sources():
    block = function_block("buildAionGoalLoopDashboardSummary")

    assert "previewAionGoalLoopCloseout" in block
    assert "previewAionGoalLoopRevisionHistory" in block
    assert "previewAionGoalLoopEvidenceProofReceipts" in block
    assert "previewAionGoalLoopApprovalGateIntegration" in block
    assert "previewAionGoalLoopCrossFunctionConflictNodes" in block
    assert "previewAionGoalLoopCanvasExecutionControls" in block


def test_phase_l2_next_action_and_safety_summary_are_locked():
    block = function_block("buildAionGoalLoopDashboardSummary")

    assert "Resolve open approval requests before execution or closeout." in block
    assert "Resolve cross-function conflicts before closeout." in block
    assert "Attach evidence and proof receipt previews before archive." in block
    assert "Send to Boardroom for final closeout decision." in block
    assert "safe_preview_only" in block
    assert "no_live_execution: true" in block
    assert "no_second_canvas: true" in block
    assert "no_second_pilot: true" in block


def test_phase_l2_renderer_exposes_visible_dashboard_panel():
    block = function_block("renderAionGoalLoopDashboardSummaryPanel")

    assert 'data-aion-goal-loop-dashboard-summary-panel="true"' in block
    assert 'data-aion-goal-loop-dashboard-business-container-id="true"' in block
    assert 'data-aion-goal-loop-dashboard-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-dashboard-open-approval-count="true"' in block
    assert 'data-aion-goal-loop-dashboard-open-conflict-count="true"' in block
    assert 'data-aion-goal-loop-dashboard-evidence-count="true"' in block
    assert 'data-aion-goal-loop-dashboard-closeout-state="true"' in block
    assert 'data-aion-goal-loop-dashboard-status-fields="true"' in block
    assert 'data-aion-goal-loop-dashboard-summary="true"' in block
    assert 'data-aion-goal-loop-dashboard-next-action="true"' in block
    assert 'data-aion-goal-loop-dashboard-safety="true"' in block
    assert 'data-aion-goal-loop-dashboard-departments="true"' in block
    assert 'data-aion-goal-loop-dashboard-preview-boundary="true"' in block


def test_phase_l2_is_preview_only_no_dashboard_write_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "dashboard_summary_preview_only: true" in block
    assert "actual_dashboard_write_performed: false" in block
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


def test_phase_l2_dashboard_is_mounted_after_l1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopCloseoutPanel()}" in APP_JS
    assert "${renderAionGoalLoopDashboardSummaryPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    l1_index = APP_JS.index("${renderAionGoalLoopCloseoutPanel()}")
    l2_index = APP_JS.index("${renderAionGoalLoopDashboardSummaryPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert l1_index < l2_index < cockpit_index
