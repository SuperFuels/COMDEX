from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o19m_installed_and_o19l_removed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19M CONSOLIDATED VOICE ONBOARDING UI LOCK" in text
    assert "O19M consolidated voice onboarding UI installed" in text
    assert "__debugAionO19MConsolidatedVoiceOnboardingUi" in text
    assert "BEGIN AION O19L LIVE MIC ONBOARDING LAUNCHER LOCK" not in text

    # O19M may keep a debug runtime check for old O19L DOM, but the actual
    # old O19L renderer/block must be gone.
    assert "data-aion-o19l-start" not in text
    assert "aion-o19l-locked" not in text
    assert "aion-o19l-active" not in text


def test_o19m_replaces_o19i_panel_renderer_not_overlaying_it():
    text = APP.read_text(encoding="utf-8")
    assert "function panelHtmlO19I(stage)" in text
    panel = text.split("function panelHtmlO19I(stage)", 1)[1].split("function ensureStylesO19I", 1)[0]
    assert "aion-o19m-clean" in panel
    assert "data-aion-o19m-start" in panel
    assert "Build your business operating system" in panel
    assert "data-aion-o19i-play-stage" in panel
    assert "data-aion-o19m-live-mic-row" in panel
    assert "data-aion-o19i-user-reply" in panel


def test_o19m_has_live_mic_and_existing_route_mapping():
    text = APP.read_text(encoding="utf-8")
    assert "window.SpeechRecognition || window.webkitSpeechRecognition" in text
    assert "recognition.continuous = true" in text
    assert "recognition.interimResults = true" in text
    assert 'data-aion-business-entry-mode="small_business_growth"' in text
    assert 'data-aion-business-entry-mode="founder_build_idea"' in text
    assert 'data-aion-business-entry-mode="founder_generate_idea"' in text


def test_o19m_clears_previous_transcript_on_start():
    text = APP.read_text(encoding="utf-8")
    assert "resetConversationState" in text
    assert 'transcript: []' in text
    assert 'stage: "startup_intro"' in text
    assert "startAionO19MOnboarding" in text
