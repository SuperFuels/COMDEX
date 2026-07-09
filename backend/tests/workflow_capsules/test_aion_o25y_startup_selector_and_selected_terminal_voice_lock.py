from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def app_text():
    return APP.read_text(encoding="utf-8")


def test_o25y_installed():
    text = app_text()
    assert "AION O25Y STARTUP SELECTOR AND SELECTED TERMINAL VOICE OWNER LOCK" in text
    assert "showStartupSelectorOnFreshLaunch" in text
    assert "clearTerminalOpenFlags" in text


def test_o25y_clears_stale_terminal_flags_on_fresh_launch():
    text = app_text()
    assert "aion.o20c.conversationOpen" in text
    assert "aion.o25u.current_terminal_open.v1" in text
    assert "aion.o25f.intentionalConversationOpen.v1" in text
    assert "window.__aionO25UConversationOpen = false" in text


def test_o25y_click_opens_terminal_and_starts_voice():
    text = app_text()
    assert "data-aion-business-entry-mode" in text
    assert "small_business_growth" in text
    assert "openSelectedTerminalFromStartup" in text
    assert "startSelectedTerminalVoice" in text
    assert "beginAionO25FAutomaticConversation" in text
    assert "speakAionO25FBusinessFoundation" in text


def test_o25y_keeps_selected_terminal_design_lock():
    text = app_text()
    assert "aion-o25e-voice-terminal" in text
    assert "AION VOICE CONVERSATION" in text
    assert "Stop talking" in text
    assert "Local voice runtime" in text
