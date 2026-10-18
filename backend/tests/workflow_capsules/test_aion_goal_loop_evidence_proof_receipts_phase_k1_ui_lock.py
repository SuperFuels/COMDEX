from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE K1")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE K1 */", start)
    return APP_JS[start:end]


def test_phase_k1_helpers_and_receipt_types_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_EVIDENCE_RECEIPT_TYPES" in block
    assert "function stableAionGoalLoopReceiptPreviewHash" in block
    assert "function buildAionGoalLoopEvidenceReceipt" in block
    assert "function previewAionGoalLoopEvidenceProofReceipts" in block
    assert "function renderAionGoalLoopEvidenceProofReceiptPanel" in block

    for receipt_type in [
        "result_node_evidence",
        "metric_snapshot_evidence",
        "evaluation_report_evidence",
        "boardroom_review_evidence",
        "approval_request_evidence",
        "cross_function_finding_evidence",
        "conflict_node_evidence",
        "persistence_plan_evidence",
        "replay_restore_evidence",
    ]:
        assert receipt_type in block


def test_phase_k1_evidence_receipt_fields_are_locked():
    block = function_block("buildAionGoalLoopEvidenceReceipt")

    for field in [
        "evidence_id",
        "receipt_id",
        "receipt_type",
        "source_id",
        "business_container_id",
        "goal_loop_id",
        "evidence_link",
        "proof_receipt_preview",
        "provenance_metadata",
        "audit_preview",
    ]:
        assert field in block

    assert "aion.goal_loop_evidence_receipt.v1" in block
    assert "aion.goal_loop_proof_receipt_preview.v1" in block
    assert "aion.goal_loop_evidence_audit_preview.v1" in block


def test_phase_k1_hash_and_proof_receipt_preview_are_present():
    block = function_block("buildAionGoalLoopEvidenceReceipt")

    assert "audit_hash_preview" in block
    assert "receipt_hash_preview" in block
    assert "canonical_payload_preview" in block
    assert "hash_algorithm_preview" in block
    assert "fnv1a_preview_only" in block
    assert "anchored: false" in block
    assert "proof_anchor_required_later: true" in block


def test_phase_k1_preview_links_result_metric_evaluation_boardroom_and_graph_edges():
    block = function_block("previewAionGoalLoopEvidenceProofReceipts")

    assert "previewAionGoalLoopReplayRestore" in block
    assert "previewAionGoalLoopBusinessContainerPersistence" in block
    assert "result_node_evidence_links" in block
    assert "metric_snapshot_evidence_links" in block
    assert "evaluation_report_evidence_links" in block
    assert "boardroom_review_evidence_links" in block
    assert "proof_receipt_previews" in block
    assert "evidence_edges" in block
    assert "proof_receipt_edges" in block


def test_phase_k1_renderer_exposes_visible_evidence_receipt_panel():
    block = function_block("renderAionGoalLoopEvidenceProofReceiptPanel")

    assert 'data-aion-goal-loop-evidence-proof-receipt-panel="true"' in block
    assert 'data-aion-goal-loop-evidence-business-container-id="true"' in block
    assert 'data-aion-goal-loop-evidence-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-evidence-receipt-count="true"' in block
    assert 'data-aion-goal-loop-evidence-safety="true"' in block
    assert 'data-aion-goal-loop-evidence-receipt-types="true"' in block
    assert 'data-aion-goal-loop-evidence-receipts="true"' in block
    assert 'data-aion-goal-loop-evidence-preview-boundary="true"' in block


def test_phase_k1_is_preview_only_no_hash_service_anchor_write_or_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "evidence_preview_only: true" in block
    assert "proof_receipt_preview_only: true" in block
    assert "actual_hash_service_called: false" in block
    assert "actual_anchor_performed: false" in block
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


def test_phase_k1_is_mounted_after_j2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopReplayRestorePanel()}" in APP_JS
    assert "${renderAionGoalLoopEvidenceProofReceiptPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    j2_index = APP_JS.index("${renderAionGoalLoopReplayRestorePanel()}")
    k1_index = APP_JS.index("${renderAionGoalLoopEvidenceProofReceiptPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert j2_index < k1_index < cockpit_index
