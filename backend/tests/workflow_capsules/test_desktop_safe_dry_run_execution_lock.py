from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def test_desktop_local_canvas_dry_run_uses_connector_preview_renderer() -> None:
    text = APP_JS.read_text()

    assert "function renderAionWorkflowLocalConnectorDryRunPreview" in text
    assert "function buildAionWorkflowLocalDryRunResult" in text
    assert "getAionWorkflowConnectorActionIdForNode(node)" in text

    # External writes must not return empty previews anymore.
    assert "output_items_preview: externalWrite\n        ? []" not in text
    assert "output_items_count: 1" in text

    # User-friendly Gmail dry-run messages must exist in desktop local preview path.
    assert "Would check Gmail for new matching messages." in text
    assert "Would create a Gmail draft after approval. No email is sent." in text
    assert "Blocked. Live email sending is not enabled." in text
    assert "Blocked. Live email replies are not enabled." in text
    assert "Blocked. Sending drafts is not enabled." in text
    assert "Blocked. Custom Gmail API calls require explicit allowlist approval." in text


def test_desktop_execution_preview_keeps_advanced_debug_collapsed() -> None:
    text = APP_JS.read_text()

    assert '<details class="aion-exec-debug">' in text
    assert "<summary>Advanced debug payload</summary>" in text
    assert "<pre>${escapeHtml(JSON.stringify(result || {}, null, 2))}</pre>" in text
