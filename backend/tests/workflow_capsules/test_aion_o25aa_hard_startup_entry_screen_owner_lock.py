from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"

def src():
    return APP.read_text(encoding="utf-8")

def test_o25aa_owner_exists():
    text = src()
    assert "AION O25AA HARD STARTUP ENTRY SCREEN OWNER LOCK" in text
    assert "installAionO25AAHardStartupEntryScreenOwner" in text
    assert "renderStartupDirect" in text
    assert "openTerminalAfterClick" in text

def test_o25aa_forces_selector_into_app_before_boardroom():
    text = src()
    assert 'document.querySelector("#app")' in text
    assert "renderBusinessEntryModeSelector()" in text
    assert "mutation_boardroom_or_terminal_bypass" in text
    assert "What are we building?" in text

def test_o25aa_terminal_requires_explicit_click():
    text = src()
    assert "aion.o25aa.explicit_terminal_open.v1" in text
    assert "data-aion-business-entry-mode=\"small_business_growth\"" in text
    assert "event.stopImmediatePropagation" in text
    assert "openTerminalAfterClick(\"small_business_growth\")" in text

def test_o25aa_clears_legacy_startup_bypass_keys():
    text = src()
    assert "aion.o20c.conversationOpen" in text
    assert "aion.o25f.intentionalConversationOpen.v1" in text
    assert "aion.voiceOnboarding.o19m.started.v1" in text
