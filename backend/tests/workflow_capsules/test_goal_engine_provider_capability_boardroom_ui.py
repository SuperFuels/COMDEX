from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_boardroom_ui_has_provider_capability_manifest_renderer():
    text = APP.read_text()

    assert "function renderAionProviderCapabilityManifestV1" in text
    assert "provider_capability_manifest" in text
    assert "Provider Capability Manifest" in text
    assert "Provider disclosure required" in text


def test_boardroom_ui_renders_provider_manifest_in_dashboard():
    text = APP.read_text()

    assert "${renderAionProviderCapabilityManifestV1(snapshot)}" in text
    assert text.index("${renderAionProviderCapabilityManifestV1(snapshot)}") > text.index(
        "${renderAionGoalEngineContainerProjectionV1(snapshot)}"
    )


def test_boardroom_ui_discloses_provider_safety_defaults():
    text = APP.read_text()

    assert "external_writes_require_approval" in text
    assert "business_state_mutations_require_human_review" in text
    assert "data-aion-provider-capability-manifest" in text
