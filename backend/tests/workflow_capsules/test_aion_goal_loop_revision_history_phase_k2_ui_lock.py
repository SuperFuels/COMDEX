from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE K2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE K2 */", start)
    return APP_JS[start:end]


def test_phase_k2_helpers_and_revision_event_types_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_REVISION_EVENT_TYPES" in block
    assert "function buildAionGoalLoopRevisionEntry" in block
    assert "function previewAionGoalLoopRevisionHistory" in block
    assert "function renderAionGoalLoopRevisionHistoryPanel" in block

    for event_type in [
        "goal_loop_created",
        "canvas_node_added",
        "department_canvas_generated",
        "task_staged",
        "approval_requested",
        "boardroom_decision_recorded",
        "result_recorded",
        "evaluation_generated",
        "ab_test_proposed",
        "feedback_sent_to_boardroom",
        "cross_function_finding_created",
        "conflict_node_created",
        "evidence_receipt_created",
        "proof_receipt_created",
        "replay_restore_planned",
    ]:
        assert event_type in block


def test_phase_k2_revision_entry_fields_are_locked():
    block = function_block("buildAionGoalLoopRevisionEntry")

    for field in [
        "revision_id",
        "event_type",
        "source_id",
        "business_container_id",
        "goal_loop_id",
        "actor",
        "source_surface",
        "before_snapshot_placeholder",
        "after_snapshot_placeholder",
        "changed_artifact_references",
        "approval_decision_references",
        "evidence_receipt_references",
        "proof_receipt_references",
        "boardroom_decision_audit_links",
        "rollback_plan_placeholder",
        "audit_metadata",
    ]:
        assert field in block

    assert "aion.goal_loop_revision_entry.v1" in block


def test_phase_k2_uses_k1_evidence_and_j1_persistence_sources():
    block = function_block("previewAionGoalLoopRevisionHistory")

    assert "previewAionGoalLoopEvidenceProofReceipts" in block
    assert "previewAionGoalLoopBusinessContainerPersistence" in block
    assert "evidence_receipts" in block
    assert "proof_receipt_previews" in block
    assert "artifact_plan" in block


def test_phase_k2_audit_trail_and_rollback_placeholders_are_locked():
    block = function_block("previewAionGoalLoopRevisionHistory")

    assert "changed_artifact_references" in block
    assert "approval_decision_references" in block
    assert "evidence_receipt_references" in block
    assert "proof_receipt_references" in block
    assert "boardroom_decision_audit_links" in block
    assert "rollback_plan_placeholders" in block
    assert "audit_trail_preview" in block
    assert "aion.goalLoopRevisionHistory.v1" in block


def test_phase_k2_renderer_exposes_visible_revision_history_panel():
    block = function_block("renderAionGoalLoopRevisionHistoryPanel")

    assert 'data-aion-goal-loop-revision-history-panel="true"' in block
    assert 'data-aion-goal-loop-revision-business-container-id="true"' in block
    assert 'data-aion-goal-loop-revision-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-revision-entry-count="true"' in block
    assert 'data-aion-goal-loop-revision-safety="true"' in block
    assert 'data-aion-goal-loop-revision-event-types="true"' in block
    assert 'data-aion-goal-loop-revision-entries="true"' in block
    assert 'data-aion-goal-loop-revision-preview-boundary="true"' in block


def test_phase_k2_is_preview_only_no_revision_write_rollback_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "revision_history_preview_only: true" in block
    assert "actual_revision_write_performed: false" in block
    assert "actual_snapshot_write_performed: false" in block
    assert "actual_rollback_performed: false" in block
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


def test_phase_k2_is_mounted_after_k1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopEvidenceProofReceiptPanel()}" in APP_JS
    assert "${renderAionGoalLoopRevisionHistoryPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    k1_index = APP_JS.index("${renderAionGoalLoopEvidenceProofReceiptPanel()}")
    k2_index = APP_JS.index("${renderAionGoalLoopRevisionHistoryPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert k1_index < k2_index < cockpit_index
