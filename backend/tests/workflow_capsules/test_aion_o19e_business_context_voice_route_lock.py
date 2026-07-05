from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o19e_route_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19E BUSINESS CONTEXT VOICE ROUTE LOCK" in text
    assert "aionOpenVoiceDiscoveryOnboardingO19E" in text
    assert "aionResetToBusinessSetupO19E" in text
    assert "aionHardResetToBusinessSetupO19E" in text
    assert "__debugAionO19EBusinessContextVoiceRoute" in text

def test_o19e_uses_business_context_not_deprecated_foundation():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O19E BUSINESS CONTEXT VOICE ROUTE LOCK", 1)[1]
    block = block.split("END AION O19E BUSINESS CONTEXT VOICE ROUTE LOCK", 1)[0]
    assert 'state.activeTab = "business_context"' in block
    assert 'window.localStorage?.setItem("aion.activeTab", "business_context")' in block
    assert 'state.activeTab = "small_business_foundation"' not in block

def test_o19e_business_context_branch_can_render_voice_screen():
    text = APP.read_text(encoding="utf-8")
    assert 'if (state.activeTab === "business_context") {' in text
    assert 'String(state.aionSmallBusinessFoundationMode || "") === "voice_conversation"' in text
    assert "window.renderAionO19BVoiceDiscoveryOnboardingScreen" in text
