from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o19c_navigation_bridge_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19C VOICE DISCOVERY NAVIGATION RESET BRIDGE LOCK" in text
    assert "aionOpenVoiceDiscoveryOnboardingO19C" in text
    assert "aionResetToStartupFoundationO19C" in text
    assert "aionClearVoiceDiscoverySessionsO19C" in text
    assert "__debugAionO19CVoiceDiscoveryNavigationResetBridge" in text

def test_o19c_uses_internal_state_not_window_state():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O19C VOICE DISCOVERY NAVIGATION RESET BRIDGE LOCK", 1)[1]
    block = block.split("END AION O19C VOICE DISCOVERY NAVIGATION RESET BRIDGE LOCK", 1)[0]
    assert 'typeof state !== "undefined"' in block
    assert 'state.activeTab = "small_business_foundation"' in block
    assert 'state.aionSmallBusinessFoundationMode = "voice_conversation"' in block
    assert "window.state.activeTab" not in block

def test_o19c_voice_session_and_reset_commands():
    text = APP.read_text(encoding="utf-8")
    assert "createAionVoiceDiscoverySessionO19A" in text
    assert "getActiveAionVoiceDiscoverySessionO19A" in text
    assert "aion.voiceDiscovery.sessions.v1" in text
    assert "aion.voiceDiscovery.activeSessionId" in text
