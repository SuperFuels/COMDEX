from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o19f_render_boundary_lock_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19F FORCE VOICE ROUTE AT RENDER BOUNDARY LOCK" in text
    assert "aion.o19f.forceVoiceRoute" in text
    assert 'state.activeTab = "business_context"' in text
    assert 'state.aionSmallBusinessFoundationMode = "voice_conversation"' in text

def test_o19f_debug_and_commands_installed():
    text = APP.read_text(encoding="utf-8")
    assert "aionForceOpenVoiceDiscoveryO19F" in text
    assert "aionForceResetBusinessSetupO19F" in text
    assert "__debugAionO19FForceVoiceRouteAtRenderBoundary" in text

def test_o19f_keeps_o19b_screen_available():
    text = APP.read_text(encoding="utf-8")
    assert "renderAionO19BVoiceDiscoveryOnboardingScreen" in text
    assert "data-aion-o19b-voice-discovery-screen" in text
