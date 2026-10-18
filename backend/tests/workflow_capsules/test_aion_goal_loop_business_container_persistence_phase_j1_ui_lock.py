from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE J1")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE J1 */", start)
    return APP_JS[start:end]


def test_phase_j1_helpers_and_storage_concepts_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_BUSINESS_CONTAINER_STORAGE_CONCEPTS" in block
    assert "function getAionGoalLoopPersistenceBusinessContainerId" in block
    assert "function buildAionGoalLoopBusinessContainerPersistencePlan" in block
    assert "function previewAionGoalLoopBusinessContainerPersistence" in block
    assert "function renderAionGoalLoopBusinessContainerPersistencePanel" in block

    for concept in [
        "aion.goalLoops.v1",
        "aion.goalLoopCanvas.v1",
        "aion.departmentGoalLoops.v1",
        "aion.boardroomGoalReview.v1",
        "aion.goalLoopEvidence.v1",
        "aion.goalLoopReceipts.v1",
        "aion.goalLoopRevisionHistory.v1",
    ]:
        assert concept in block


def test_phase_j1_uses_registered_business_container_resolver_and_blocks_stale_legacy():
    block = function_block("getAionGoalLoopPersistenceBusinessContainerId")

    assert "getAionBackendBusinessEndpointId" in block
    assert "getAionWorkflowBusinessContainerId" in block
    assert "isAionLegacyDemoBusinessIdentity" in block
    assert "business_not_registered" in block


def test_phase_j1_persistence_plan_artifacts_are_locked():
    block = function_block("buildAionGoalLoopBusinessContainerPersistencePlan")

    for artifact in [
        "master_goal_loop_canvas",
        "goal_loop_json",
        "department_canvases",
        "execution_runs",
        "measurement_snapshots",
        "evaluation_reports",
        "ab_test_proposals",
        "feedback_nodes",
        "cross_function_findings",
        "approval_requests",
        "evidence_receipts_placeholder",
        "proof_receipts_placeholder",
        "revision_history_placeholder",
    ]:
        assert artifact in block

    assert "aion.goal_loop_business_container_persistence_plan.v1" in block
    assert "aion.department_goal_loop_persistence_plan.v1" in block


def test_phase_j1_department_sub_container_plan_is_generic():
    block = function_block("buildAionGoalLoopBusinessContainerPersistencePlan")

    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert department in block

    assert "department_canvas" in block
    assert "department_tasks" in block
    assert "department_metrics" in block
    assert "department_results" in block
    assert "department_feedback" in block


def test_phase_j1_renderer_exposes_visible_persistence_plan_panel():
    block = function_block("renderAionGoalLoopBusinessContainerPersistencePanel")

    assert 'data-aion-goal-loop-business-container-persistence-panel="true"' in block
    assert 'data-aion-goal-loop-persistence-business-container-id="true"' in block
    assert 'data-aion-goal-loop-persistence-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-persistence-artifact-count="true"' in block
    assert 'data-aion-goal-loop-persistence-safety="true"' in block
    assert 'data-aion-goal-loop-persistence-storage-concepts="true"' in block
    assert 'data-aion-goal-loop-persistence-artifacts="true"' in block
    assert 'data-aion-goal-loop-persistence-departments="true"' in block
    assert 'data-aion-goal-loop-persistence-preview-boundary="true"' in block


def test_phase_j1_is_plan_preview_only_no_actual_writes_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "persistence_preview_only: true" in block
    assert "write_required_now: false" in block
    assert "actual_container_write_performed: false" in block
    assert "external_side_effects: false" in block
    assert "connector_call_required: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block

    assert "fetch(" not in forbidden
    assert "apiPost(" not in block
    assert "writeFile" not in block
    assert "localStorage.setItem" not in block
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden
    assert "payment_created: true" not in forbidden
    assert "booking_created: true" not in forbidden


def test_phase_j1_is_mounted_after_i2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopApprovalGatePanel()}" in APP_JS
    assert "${renderAionGoalLoopBusinessContainerPersistencePanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    i2_index = APP_JS.index("${renderAionGoalLoopApprovalGatePanel()}")
    j1_index = APP_JS.index("${renderAionGoalLoopBusinessContainerPersistencePanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert i2_index < j1_index < cockpit_index
