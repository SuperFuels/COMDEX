from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_generated_workflow_edit_validate_save_contract_is_locked() -> None:
    text = APP.read_text()

    assert "function markAionWorkflowGraphEdited" in text
    assert "function preserveAionWorkflowArchitectMetadata" in text
    assert "function validateAionWorkflowGraphBeforeSave" in text
    assert "function confirmAionWorkflowCapsuleSave" in text

    assert "edited_after_architect_review" in text
    assert "metadata_preserved" in text
    assert "last_dry_run_at" in text
    assert "save_confirmed_at" in text

    assert "workflow_save_blocked:dry_run_required_after_edit" in text
    assert "workflow_save_blocked:live_send_action" in text
    assert '["users", "messages", "send"].join(".")' in text

    assert "saveAionWorkflowCanvasAsCapsule" in text
    assert "confirmAionWorkflowCapsuleSave(safeGraph)" in text


def test_generated_node_edit_preserves_architect_metadata_before_compile() -> None:
    text = APP.read_text()

    assert "preserveAionWorkflowArchitectMetadata(node" in text
    assert "markAionWorkflowGraphEdited(\"node_config_edit\")" in text
    assert "compileAndAttachAionWorkflowGlyph(graph)" in text
    assert "persistAionWorkflowDraftState()" in text
