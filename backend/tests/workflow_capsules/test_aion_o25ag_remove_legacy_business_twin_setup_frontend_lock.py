from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def read_app():
    return APP_JS.read_text(encoding="utf-8")


def test_legacy_business_twin_setup_frontend_renderer_removed():
    text = read_app()

    assert "installAionBusinessTwinSetupV1" not in text
    assert "showBusinessTwinSetup" not in text
    assert "renderBusinessTwinSetup" not in text
    assert "data-aion-business-twin-setup-root" not in text


def test_legacy_business_twin_setup_user_facing_copy_removed():
    text = read_app()

    assert "AION does not guess your business" not in text
    assert "Start Business Twin Setup" not in text
    assert "Continue in Limited Context Mode" not in text
    assert "[RETIRED O25AF LEGACY BUSINESS TWIN SETUP REMOVED" not in text


def test_old_hide_patch_and_old_voice_guide_removed():
    text = read_app()

    assert "BEGIN AION O25AF REMOVE LEGACY BUSINESS TWIN SETUP FRONTEND LOCK" not in text
    assert "BEGIN AION O19I VOICE GUIDE ON EXISTING BUSINESS TWIN FLOW LOCK" not in text
    assert "O25AF legacy Business Twin Setup frontend removed" not in text
    assert "O19I voice guide on existing Business Twin flow" not in text
