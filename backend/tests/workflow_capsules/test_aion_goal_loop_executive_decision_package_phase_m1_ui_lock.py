from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE M1")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE M1 */", start)
    return APP_JS[start:end]


def test_phase_m1_helpers_and_decision_outcomes_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_EXECUTIVE_DECISION_OUTCOMES" in block
    assert "function buildAionGoalLoopExecutiveDecisionPackage" in block
    assert "function previewAionGoalLoopExecutiveDecisionPackage" in block
    assert "function renderAionGoalLoopExecutiveDecisionPackagePanel" in block

    for outcome in [
        "approve_closeout",
        "approve_next_action",
        "request_more_data",
        "resolve_blockers_first",
        "pause_goal_loop",
        "archive_goal_loop",
        "extend_goal_loop",
    ]:
        assert outcome in block


def test_phase_m1_decision_package_fields_are_locked():
    block = function_block("buildAionGoalLoopExecutiveDecisionPackage")

    for field in [
        "executive_question",
        "goal_summary",
        "department_conclusions",
        "approval_summary",
        "conflict_summary",
        "evidence_summary",
        "revision_audit_summary",
        "persistence_impact_summary",
        "blocker_summary",
        "final_recommendation",
        "if_approved_preview",
        "boardroom_decision_record_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_executive_decision_package.v1" in block


def test_phase_m1_uses_full_b_to_l_goal_loop_chain_sources():
    block = function_block("buildAionGoalLoopExecutiveDecisionPackage")

    assert "previewAionGoalLoopDashboardSummary" in block
    assert "previewAionGoalLoopCloseout" in block
    assert "previewAionGoalLoopBusinessContainerPersistence" in block
    assert "previewAionGoalLoopApprovalGateIntegration" in block
    assert "previewAionGoalLoopCrossFunctionConflictNodes" in block
    assert "previewAionGoalLoopEvidenceProofReceipts" in block
    assert "previewAionGoalLoopRevisionHistory" in block


def test_phase_m1_recommendation_and_if_approved_preview_are_locked():
    block = function_block("buildAionGoalLoopExecutiveDecisionPackage")

    assert "resolve_blockers_first" in block
    assert "approve_closeout" in block
    assert "approve_next_action" in block
    assert "Stage final closeout/archive handoff preview." in block
    assert "Return to approval/conflict/evidence resolution previews." in block
    assert "Stage next Goal Loop action preview." in block
    assert "will_execute_now: false" in block
    assert "will_persist_now: false" in block
    assert "will_archive_now: false" in block
    assert "will_contact_external_systems_now: false" in block


def test_phase_m1_renderer_exposes_visible_executive_decision_package_panel():
    block = function_block("renderAionGoalLoopExecutiveDecisionPackagePanel")

    assert 'data-aion-goal-loop-executive-decision-package-panel="true"' in block
    assert 'data-aion-goal-loop-exec-package-business-container-id="true"' in block
    assert 'data-aion-goal-loop-exec-package-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-exec-package-recommendation="true"' in block
    assert 'data-aion-goal-loop-exec-package-blocker-count="true"' in block
    assert 'data-aion-goal-loop-exec-package-outcomes="true"' in block
    assert 'data-aion-goal-loop-exec-package-summary="true"' in block
    assert 'data-aion-goal-loop-exec-package-if-approved="true"' in block
    assert 'data-aion-goal-loop-exec-package-departments="true"' in block
    assert 'data-aion-goal-loop-exec-package-preview-boundary="true"' in block


def test_phase_m1_is_preview_only_no_decision_execution_persistence_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "executive_decision_package_preview_only: true" in block
    assert "actual_decision_write_performed: false" in block
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


def test_phase_m1_is_mounted_after_l2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopDashboardSummaryPanel()}" in APP_JS
    assert "${renderAionGoalLoopExecutiveDecisionPackagePanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    l2_index = APP_JS.index("${renderAionGoalLoopDashboardSummaryPanel()}")
    m1_index = APP_JS.index("${renderAionGoalLoopExecutiveDecisionPackagePanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert l2_index < m1_index < cockpit_index
