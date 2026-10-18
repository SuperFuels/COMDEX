from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o19b_ui_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19B VOICE DISCOVERY ONBOARDING UI LOCK" in text
    assert "renderAionO19BVoiceDiscoveryOnboardingScreen" in text
    assert "__debugAionO19BVoiceDiscoveryOnboardingUI" in text

def test_o19b_start_conversation_card_and_manual_fallback():
    text = APP.read_text(encoding="utf-8")
    assert "Start with a conversation" in text
    assert "Recommended setup path" in text
    assert "data-aion-o19b-start-conversation" in text
    assert "data-aion-o19b-manual-setup" in text
    assert "previousRenderBusinessEntryModeSelectorO19B.apply" in text

def test_o19b_text_only_dev_screen_contract():
    text = APP.read_text(encoding="utf-8")
    assert "data-aion-o19b-voice-discovery-screen" in text
    assert "data-aion-o19b-transcript-input" in text
    assert "data-aion-o19b-send-turn" in text
    assert "data-aion-o19b-build-summary" in text
    assert "data-aion-o19b-confirm-summary" in text
    assert "text_only_dev_adapter" in text

def test_o19b_uses_o19a_contract():
    text = APP.read_text(encoding="utf-8")
    assert "createAionVoiceDiscoverySessionO19A" in text
    assert "appendAionVoiceDiscoveryTranscriptO19A" in text
    assert "buildAionVoiceDiscoveryConfirmationSummaryO19A" in text
    assert "confirmAionVoiceDiscoverySessionO19A" in text
    assert "discardAionVoiceDiscoverySessionO19A" in text

def test_o19b_safety_copy_present():
    text = APP.read_text(encoding="utf-8")
    assert "no emails, ads, bookings, payments or invoices" in text
    assert "Raw audio" in text
    assert "not stored by default" in text
    assert "provider-abstract contract" in text
