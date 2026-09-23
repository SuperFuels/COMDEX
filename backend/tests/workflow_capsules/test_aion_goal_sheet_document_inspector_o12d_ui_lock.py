from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12d_document_inspector_installed():
    assert "BEGIN AION O12D GOAL SHEET DOCUMENT NODE INSPECTOR" in APP_JS
    assert "openAionGoalSheetDocumentInspectorO12D" in APP_JS
    assert "getAionGoalSheetNodePayloadO12D" in APP_JS
    assert "isAionGoalSheetNodeClickO12D" in APP_JS


def test_o12d_goal_sheet_click_takeover_blocks_generic_editor():
    assert "[data-aion-workflow-node-id]" in APP_JS
    assert "event.stopImmediatePropagation()" in APP_JS
    assert "openAionGoalSheetDocumentInspectorO12D(nodeId)" in APP_JS


def test_o12d_inspector_has_document_specific_payloads():
    assert "meeting_minutes" in APP_JS
    assert "boardroom_decision" in APP_JS
    assert "actual_goal" in APP_JS
    assert "success_criteria" in APP_JS
    assert "linked_department_sheets" in APP_JS
    assert "pilot_queue_preview" in APP_JS
    assert "evidence_feedback" in APP_JS


def test_o12d_linked_department_sheet_buttons_exist():
    assert "data-aion-o12d-open-department-sheet" in APP_JS
    assert "data-aion-o12b-open-linked-workflow" in APP_JS
    assert "openAionLinkedDepartmentGoalSheetO12D" in APP_JS
    assert "window.__aionGoalLoopDepartmentGoalSheets" in APP_JS
    assert "window.__aionGoalLoopLinkedWorkflowRegistry" in APP_JS


def test_o12d_inspector_preserves_preview_safety():
    assert "preview_only: true" in APP_JS
    assert "execution_allowed_now: false" in APP_JS
    assert "connector_call_required: false" in APP_JS
    assert "external_side_effects: false" in APP_JS
    assert "approval_required: true" in APP_JS
