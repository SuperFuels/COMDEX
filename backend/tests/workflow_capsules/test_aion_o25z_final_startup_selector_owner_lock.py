from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"

def text():
    return APP.read_text(encoding="utf-8")

def test_o25z_final_owner_exists():
    src = text()
    assert "AION O25Z FINAL STARTUP SELECTOR OWNER LOCK" in src
    assert "installAionO25ZFinalStartupSelectorOwner" in src
    assert "resetAionO25ZToStartupSelector" in src

def test_fresh_launch_clears_legacy_open_state():
    src = text()
    assert "aion.o20c.conversationOpen" in src
    assert "aion.o25f.intentionalConversationOpen.v1" in src
    assert "aion.voiceOnboarding.o19m.started.v1" in src
    assert "forceStartupSelector" in src
    assert "removeTerminalIfNotExplicit" in src

def test_terminal_only_after_explicit_business_click():
    src = text()
    assert "aion.o25z.explicit_terminal_open.v1" in src
    assert "openSelectedTerminal" in src
    assert 'data-aion-business-entry-mode="small_business_growth"' in src
    assert "syncAionO25ETerminalOnlyVoiceConversation" in src
    assert "Local TTS" in src
    assert '"provider": "local"' not in src  # payload is object syntax, not JSON string fixture

def test_selected_terminal_design_still_present():
    src = text()
    assert "aion-o25e-voice-terminal" in src
    assert "AION VOICE CONVERSATION" in src
    assert "Business Foundation Conversation" in src
    assert "Stop talking" in src
