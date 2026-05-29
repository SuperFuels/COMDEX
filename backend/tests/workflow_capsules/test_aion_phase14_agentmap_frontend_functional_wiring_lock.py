from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text():
    return APP.read_text()


def test_phase14i_agentmap_frontend_functional_panel_is_mounted():
    text = _text()

    # Phase 14M removed the duplicate machine discovery panel from Boardroom.
    # The legacy renderer may remain for compatibility, but it must not be actively mounted.
    assert "function renderAgentMapMachineDiscoveryPanel()" in text
    assert "function renderAgentMapDashboardPanel()" in text
    assert "${renderAgentMapDashboardPanel()}" in text
    assert "${renderAgentMapMachineDiscoveryPanel()}" not in text

def test_phase14i_generate_button_is_real_and_wired_to_state():
    text = _text()
    assert 'id="agentmapGenerateButton"' in text
    assert 'data-agentmap-action="generate"' in text
    assert "function handleGenerateAgentMapClick()" in text
    assert "state.agentMapDashboardPreview" in text
    assert "state.agentMapGenerated" in text
    assert "requestRender?.()" in text


def test_phase14i_machine_discovery_settings_are_rendered():
    text = _text()
    for term in [
        "Machine Discovery Settings",
        "preview_only",
        "human_review_required",
        "live_execution_enabled",
        "Hosted AgentMap URL",
        "Self-hosted export",
    ]:
        assert term in text


def test_phase14i_agentmap_preview_and_hash_are_visible():
    text = _text()
    for term in [
        "Generated agentmap.json Preview",
        "agentmapJsonPreview",
        "agentmap_hash",
        "verification_badge",
        "AgentMap Verified Live",
        "Phase 14D live verification",
    ]:
        assert term in text


def test_phase14i_hosted_and_self_hosted_paths_are_bound():
    text = _text()
    assert "/agentmap.json" in text
    assert "/.well-known/agentmap.json" in text
    assert "hosted_agentmap_url" in text
    assert "self_hosted_agentmap_url" in text


def test_phase14i_frontend_lock_does_not_enable_live_side_effects():
    text = _text()
    forbidden = [
        "capturePayment(",
        "createBooking(",
        "releaseEscrow(",
        "dispatchJob(",
        "sendExternalMessage(",
        "live_execution_enabled: true",
    ]
    for item in forbidden:
        assert item not in text
