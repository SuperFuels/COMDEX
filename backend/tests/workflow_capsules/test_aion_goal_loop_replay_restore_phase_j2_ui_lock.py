from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE J2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE J2 */", start)
    return APP_JS[start:end]


def test_phase_j2_helpers_and_restore_sections_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_REPLAY_RESTORE_SECTIONS" in block
    assert "function buildAionGoalLoopReplayRestorePlan" in block
    assert "function previewAionGoalLoopReplayRestore" in block
    assert "function renderAionGoalLoopReplayRestorePanel" in block

    for section in [
        "active_goal_loop",
        "graph_nodes",
        "graph_edges",
        "department_child_canvases",
        "metrics",
        "evaluations",
        "ab_test_proposals",
        "boardroom_review_state",
        "feedback_nodes",
        "cross_function_findings",
        "conflict_nodes",
        "approval_requests",
        "evidence_links",
    ]:
        assert section in block


def test_phase_j2_uses_j1_persistence_plan_and_registered_business_resolver():
    block = function_block("buildAionGoalLoopReplayRestorePlan")

    assert "previewAionGoalLoopBusinessContainerPersistence" in block
    assert "getAionGoalLoopPersistenceBusinessContainerId" in block
    assert "isAionLegacyDemoBusinessIdentity" in block
    assert "business_not_registered" in block
    assert "stale_legacy_business_blocked" in block
    assert "registered_business_resolver_used: true" in block


def test_phase_j2_restore_plan_fields_are_locked():
    block = function_block("buildAionGoalLoopReplayRestorePlan")

    for field in [
        "restore_sections",
        "department_restore_plan",
        "graph_restore_preview",
        "boardroom_restore_preview",
        "actual_container_read_performed",
        "actual_restore_performed",
        "replay_restore_preview_only",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_replay_restore_plan.v1" in block
    assert "aion.goal_loop_replay_restore_section.v1" in block
    assert "aion.department_goal_loop_replay_restore_plan.v1" in block


def test_phase_j2_graph_and_boardroom_restore_preview_are_complete():
    block = function_block("buildAionGoalLoopReplayRestorePlan")

    for item in [
        "restore_nodes",
        "restore_edges",
        "restore_department_child_canvases",
        "restore_metrics",
        "restore_evaluations",
        "restore_ab_test_proposals",
        "restore_feedback_nodes",
        "restore_cross_function_findings",
        "restore_conflict_nodes",
        "restore_approval_requests",
        "restore_evidence_links",
        "restore_boardroom_review_state",
        "restore_boardroom_decisions",
        "restore_approval_reviews",
    ]:
        assert item in block


def test_phase_j2_renderer_exposes_visible_replay_restore_panel():
    block = function_block("renderAionGoalLoopReplayRestorePanel")

    assert 'data-aion-goal-loop-replay-restore-panel="true"' in block
    assert 'data-aion-goal-loop-restore-business-container-id="true"' in block
    assert 'data-aion-goal-loop-restore-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-restore-section-count="true"' in block
    assert 'data-aion-goal-loop-restore-safety="true"' in block
    assert 'data-aion-goal-loop-restore-sections="true"' in block
    assert 'data-aion-goal-loop-restore-section-list="true"' in block
    assert 'data-aion-goal-loop-restore-departments="true"' in block
    assert 'data-aion-goal-loop-restore-preview-boundary="true"' in block


def test_phase_j2_is_restore_preview_only_no_actual_reads_writes_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "replay_restore_preview_only: true" in block
    assert "actual_container_read_performed: false" in block
    assert "actual_restore_performed: false" in block
    assert "actual_graph_mutation_performed: false" in block
    assert "actual_boardroom_state_mutation_performed: false" in block
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


def test_phase_j2_is_mounted_after_j1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopBusinessContainerPersistencePanel()}" in APP_JS
    assert "${renderAionGoalLoopReplayRestorePanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    j1_index = APP_JS.index("${renderAionGoalLoopBusinessContainerPersistencePanel()}")
    j2_index = APP_JS.index("${renderAionGoalLoopReplayRestorePanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert j1_index < j2_index < cockpit_index
