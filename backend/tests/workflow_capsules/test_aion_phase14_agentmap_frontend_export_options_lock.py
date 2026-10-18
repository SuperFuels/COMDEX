from pathlib import Path

APP = Path("desktop/mac/src/app.js")
DOC = Path("docs/rfc/aion_phase14_agentmap_frontend_export_options_lock.tex")


def _app_text():
    return APP.read_text()


def test_phase14k_frontend_export_options_helpers_exist():
    text = _app_text()
    assert "buildAgentMapHostedExportOptions" in text
    assert "renderAgentMapHostedSelfHostedOptions" in text
    assert "getAgentMapSelfHostedExportPayload" in text


def test_phase14k_hosted_url_option_is_visible():
    text = _app_text()
    assert "data-agentmap-hosted-url-option" in text
    assert "data-agentmap-hosted-url-value" in text
    assert "hosted_agentmap_url" in text
    assert "/agentmap.json" in text


def test_phase14k_self_hosted_export_option_is_visible():
    text = _app_text()
    assert "data-agentmap-self-hosted-export-option" in text
    assert "data-agentmap-self-hosted-path-value" in text
    assert "/.well-known/agentmap.json" in text


def test_phase14k_export_remains_preview_only():
    text = _app_text()
    assert "data-agentmap-export-preview-only" in text
    assert "preview_only: true" in text
    assert "live_publish_enabled: false" in text
    assert "Preview only · live publish disabled" in text


def test_phase14k_self_hosted_payload_declares_json_contract():
    text = _app_text()
    assert 'filename: "agentmap.json"' in text
    assert 'content_type: "application/json"' in text
    assert "agentmap_json" in text


def test_phase14k_lock_doc_exists_and_names_contract():
    assert DOC.exists()
    text = DOC.read_text().lower()
    for term in [
        "phase 14k",
        "hosted agentmap url",
        "self-hosted",
        ".well-known/agentmap.json",
        "preview only",
        "lock id:",
        "maintainer: tessaris ai",
        "author: kevin robinson",
    ]:
        assert term in text
