from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text():
    return APP.read_text()


def test_phase14n_agentmap_payload_normaliser_exists():
    text = _text()
    assert "function normaliseAgentMapDashboardPreviewPayload(payload)" in text
    assert "function getAgentMapDashboardPreviewPayload()" in text


def test_phase14n_agentmap_json_aliases_legacy_agentmap_preview():
    text = _text()
    assert "source.agentmap_json ||" in text
    assert "source.agentmap_preview ||" in text
    assert "agentmap_json: agentmapJson" in text
    assert "agentmap_preview: agentmapJson" in text


def test_phase14n_safety_profile_falls_back_from_agentmap_json():
    text = _text()
    assert "source.safety_profile ||" in text
    assert "agentmapJson.safety_profile ||" in text
    assert "safety_profile: safetyProfile" in text
    assert "preview_only: true" in text
    assert "human_review_required: true" in text
    assert "live_execution_enabled: false" in text


def test_phase14n_urls_and_hash_are_normalised():
    text = _text()
    assert "agentmap_hash:" in text
    assert "agentmapJson.agentmap_hash" in text
    assert "hosted_agentmap_url:" in text
    assert "self_hosted_agentmap_url:" in text
    assert '"/agentmap.json"' in text
    assert '"/.well-known/agentmap.json"' in text


def test_phase14n_canonical_panel_reads_normalised_fields():
    text = _text()
    start = text.find("function renderAgentMapDashboardPanel")
    end = text.find("function renderBoardroomDashboardView")
    assert start != -1
    assert end != -1
    panel = text[start:end]
    assert "preview.safety_profile || {}" in panel
    assert "preview.agentmap_json" in panel
    assert "undefined" not in panel
