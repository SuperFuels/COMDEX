from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "desktop/mac/src/styles.css").read_text(encoding="utf-8")


def test_saved_workflows_expand_from_sticky_footer_not_document_tabs():
    assert 'data-aion-saved-workflows-dropup="true"' in APP
    assert 'data-aion-saved-workflows-menu="true"' in APP
    assert '<strong>Saved</strong>' in APP
    assert '<strong>Saved workflows</strong>' not in APP
    assert 'data-aion-workflow-page-tab="saved"' not in APP
    assert 'data-aion-phase19b-saved-workflows' not in APP
    assert 'data-aion-executive-automations="true"' not in APP
    assert "Train Agent and workflow activity" not in APP


def test_saved_workflow_index_removes_seeded_and_placeholder_records():
    assert '"workflow_social_post", "workflow_campaign_approval"' in APP
    assert "/^untitled workflow" in APP
    assert "/^workflow \\d+$/i" in APP
    assert "sanitiseAionFileCabinetTreeV1" in APP
    assert "const identity = `${department}:" in APP


def test_saved_workflows_are_visible_in_business_files():
    assert 'data-aion-file-cabinet-saved-index="true"' in APP
    assert "getAionSavedWorkflowLibraryV1()" in APP
    assert ".aion-saved-workflows-dropup" in STYLES
    assert ".aion-saved-workflows-menu" in STYLES
