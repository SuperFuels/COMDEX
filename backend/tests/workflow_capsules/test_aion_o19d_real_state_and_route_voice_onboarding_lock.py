from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o19d_real_state_bridge_after_desktop_state():
    text = APP.read_text(encoding="utf-8")
    assert "const state = desktopStore.state;" in text
    assert "BEGIN AION O19D REAL STATE AND ROUTE VOICE ONBOARDING LOCK" in text
    assert text.index("const state = desktopStore.state;") < text.index("BEGIN AION O19D REAL STATE AND ROUTE VOICE ONBOARDING LOCK")
    assert "aionOpenVoiceDiscoveryOnboardingO19D" in text
    assert "aionResetToStartupFoundationO19D" in text
    assert "aionHardResetToStartupO19D" in text
    assert "__debugAionO19DRealStateVoiceNavBridge" in text

def test_o19d_uses_real_state_and_not_window_state():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O19D REAL STATE AND ROUTE VOICE ONBOARDING LOCK", 1)[1]
    block = block.split("END AION O19D REAL STATE AND ROUTE VOICE ONBOARDING LOCK", 1)[0]
    assert 'state.activeTab = "small_business_foundation"' in block
    assert 'state.aionSmallBusinessFoundationMode = "voice_conversation"' in block
    assert "window.state" not in block

def test_o19d_allows_voice_on_deprecated_small_business_route():
    text = APP.read_text(encoding="utf-8")
    assert 'String(state?.aionSmallBusinessFoundationMode || "") !== "voice_conversation"' in text

def test_o19d_business_entry_wrapper_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19D BUSINESS ENTRY VOICE WRAPPER LOCK" in text
    assert "renderBusinessEntryModeSelectorWithVoiceDiscoveryO19D" in text
    assert "data-aion-o19d-start-conversation-card" in text
    assert "window.renderAionO19BVoiceDiscoveryOnboardingScreen" in text
    assert "window.aionOpenVoiceDiscoveryOnboardingO19D" in text
