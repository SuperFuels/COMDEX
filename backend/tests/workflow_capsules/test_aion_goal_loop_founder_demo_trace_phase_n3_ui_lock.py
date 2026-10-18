from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE N3")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE N3 */", start)
    return APP_JS[start:end]


def test_phase_n3_helpers_and_full_phase_chain_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_FOUNDER_DEMO_TRACE_PHASES" in block
    assert "function buildAionGoalLoopFounderDemoTrace" in block
    assert "function previewAionGoalLoopFounderDemoTrace" in block
    assert "function renderAionGoalLoopFounderDemoTracePanel" in block

    for phase_id in [
        "B1_canvas_contract",
        "C1_boardroom_create",
        "D3_central_pilot_safe_queue",
        "E3_evaluation_engine",
        "F2_generate_ab_test_from_evaluation",
        "G2_boardroom_feedback_decision",
        "H2_cross_function_conflict_nodes",
        "I2_approval_gate_integration",
        "J2_replay_restore_preview",
        "K2_revision_history_audit_trail",
        "L2_goal_loop_dashboard_summary",
        "M2_boardroom_decision_capture",
        "N2_guarded_execution_handoff",
        "N3_founder_demo_trace",
    ]:
        assert phase_id in block


def test_phase_n3_trace_fields_are_locked():
    block = function_block("buildAionGoalLoopFounderDemoTrace")

    for field in [
        "full_phase_chain_summary",
        "business_identity_source_check",
        "canvas_reuse_check",
        "central_pilot_reuse_check",
        "department_pilot_reuse_check",
        "all_preview_artifacts",
        "boardroom_decision_path",
        "guarded_execution_handoff_path",
        "safety_boundary_matrix",
        "founder_demo_readiness_status",
        "manual_test_plan_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_founder_demo_trace.v1" in block


def test_phase_n3_uses_recent_preview_chain_sources():
    block = function_block("buildAionGoalLoopFounderDemoTrace")

    assert "previewAionGoalLoopGuardedExecutionHandoff" in block
    assert "previewAionGoalLoopApprovedActionStaging" in block
    assert "previewAionGoalLoopBoardroomDecisionCapture" in block
    assert "previewAionGoalLoopExecutiveDecisionPackage" in block
    assert "previewAionGoalLoopDashboardSummary" in block
    assert "previewAionGoalLoopCloseout" in block
    assert "previewAionGoalLoopEvidenceProofReceipts" in block
    assert "previewAionGoalLoopRevisionHistory" in block


def test_phase_n3_identity_canvas_and_pilot_reuse_boundaries_are_locked():
    block = function_block("buildAionGoalLoopFounderDemoTrace")

    assert "registered_business_information" in block
    assert "hard_coded_business_default_allowed: false" in block
    assert "stale_runtime_identity_allowed: false" in block
    assert "existing_workflow_canvas_reused: true" in block
    assert "new_canvas_created: false" in block
    assert "existing_central_pilot_reused: true" in block
    assert "new_central_pilot_created: false" in block
    assert "existing_department_pilot_surfaces_reused: true" in block
    assert "department_scope_preserved: true" in block


def test_phase_n3_renderer_exposes_visible_founder_demo_trace_panel():
    block = function_block("renderAionGoalLoopFounderDemoTracePanel")

    assert 'data-aion-goal-loop-founder-demo-trace-panel="true"' in block
    assert 'data-aion-goal-loop-founder-trace-business-container-id="true"' in block
    assert 'data-aion-goal-loop-founder-trace-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-founder-trace-readiness="true"' in block
    assert 'data-aion-goal-loop-founder-trace-safety="true"' in block
    assert 'data-aion-goal-loop-founder-trace-summary="true"' in block
    assert 'data-aion-goal-loop-founder-trace-identity-source="true"' in block
    assert 'data-aion-goal-loop-founder-trace-reuse-check="true"' in block
    assert 'data-aion-goal-loop-founder-trace-boardroom-path="true"' in block
    assert 'data-aion-goal-loop-founder-trace-handoff-path="true"' in block
    assert 'data-aion-goal-loop-founder-trace-phases="true"' in block
    assert 'data-aion-goal-loop-founder-trace-preview-boundary="true"' in block


def test_phase_n3_is_preview_only_no_trace_write_execution_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "founder_demo_trace_preview_only: true" in block
    assert "actual_trace_write_performed: false" in block
    assert "actual_queue_write_performed: false" in block
    assert "actual_decision_write_performed: false" in block
    assert "actual_approval_write_performed: false" in block
    assert "actual_execution_performed: false" in block
    assert "actual_connector_call_performed: false" in block
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


def test_phase_n3_is_mounted_after_n2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopGuardedExecutionHandoffPanel()}" in APP_JS
    assert "${renderAionGoalLoopFounderDemoTracePanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    n2_index = APP_JS.index("${renderAionGoalLoopGuardedExecutionHandoffPanel()}")
    n3_index = APP_JS.index("${renderAionGoalLoopFounderDemoTracePanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert n2_index < n3_index < cockpit_index
