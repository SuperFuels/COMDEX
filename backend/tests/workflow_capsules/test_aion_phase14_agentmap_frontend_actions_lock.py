from pathlib import Path

APP = Path("desktop/mac/src/app.js")
DOC = Path("docs/rfc/aion_phase14_agentmap_frontend_actions_lock.tex")


def _text(path: Path) -> str:
    return path.read_text()


def test_phase14j_agentmap_frontend_actions_are_visible():
    text = _text(APP)
    for term in [
        "data-agentmap-generate-button",
        "data-agentmap-regenerate-button",
        "data-agentmap-copy-url-button",
        "data-agentmap-download-json-button",
        "data-agentmap-copy-install-tag-button",
        "data-agentmap-json-preview",
        "data-machine-discovery-settings-panel",
        "data-agentmap-validation-status",
    ]:
        assert term in text


def test_phase14j_agentmap_actions_have_handlers():
    text = _text(APP)
    for term in [
        "function handleGenerateAgentMapPreview",
        "function handleRegenerateAgentMapPreview",
        "function handleCopyAgentMapUrl",
        "function handleDownloadAgentMapJson",
        "function handleCopyAgentMapInstallTag",
        "function copyAgentMapValue",
    ]:
        assert term in text


def test_phase14j_agentmap_download_uses_json_blob_not_live_publish():
    text = _text(APP)
    assert "new Blob([json], { type: \"application/json\" })" in text
    assert "link.download = \"agentmap.json\"" in text

    for term in [
        "publishAgentMap(",
        "createBooking(",
        "capturePayment(",
        "releaseEscrow(",
        "dispatchJob(",
        "writeLiveChain(",
    ]:
        assert term not in text


def test_phase14j_agentmap_copy_actions_use_clipboard_only():
    text = _text(APP)
    assert "navigator?.clipboard?.writeText" in text
    assert "handleCopyAgentMapUrl" in text
    assert "handleCopyAgentMapInstallTag" in text


def test_phase14j_agentmap_regenerate_refreshes_preview_state():
    text = _text(APP)
    assert "agentMapDashboardGenerationCount" in text
    assert "agentMapDashboardPreview = buildAgentMapDashboardPreviewPayload()" in text
    assert "agentMapDashboardLastAction = \"regenerated\"" in text


def test_phase14j_doc_exists_and_mentions_lock_terms():
    assert DOC.exists()
    text = _text(DOC).lower()
    for term in [
        "phase 14j",
        "copy agentmap url",
        "download agentmap.json",
        "copy website install tag",
        "regenerate",
        "preview-only",
        "human review",
        "lock id:",
        "maintainer: tessaris ai",
        "author: kevin robinson",
    ]:
        assert term in text
