from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o20c_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O20C CONVERSATION TAKEOVER STYLE LOCK" in text
    assert "BEGIN AION O20C CONVERSATION TAKEOVER BEHAVIOUR LOCK" in text
    assert "__debugAionO20CConversationTakeover" in text
    assert "openAionO20CConversation" in text


def test_o20c_removes_provider_icon_row_from_startup_renderer():
    text = APP.read_text(encoding="utf-8")
    block = text.split("function renderBusinessEntryModeSelector()", 1)[1].split("/* BEGIN AION O19F STARTUP SELECTOR CONSOLE ROUTE HELPERS", 1)[0]
    assert "aion-o20b-council" not in block
    assert "Powered by Glyph OS · Wave Intelligence" in block
    assert "AION\n            <small>always on</small>" not in block
    assert "Gemma\n            <small>connected</small>" not in block
    assert "OpenAI" not in block
    assert "Claude" not in block
    assert "Gemini" not in block
    assert "Grok" not in block


def test_o20c_all_start_buttons_open_conversation():
    text = APP.read_text(encoding="utf-8")
    block = text.split("function renderBusinessEntryModeSelector()", 1)[1].split("/* BEGIN AION O19F STARTUP SELECTOR CONSOLE ROUTE HELPERS", 1)[0]
    assert 'data-aion-o20c-open-conversation="start_with_aion"' in block
    assert 'data-aion-o20c-open-conversation="small_business_growth"' in block
    assert 'data-aion-o20c-open-conversation="founder_build_idea"' in block
    assert 'data-aion-o20c-open-conversation="founder_generate_idea"' in block
    assert 'data-aion-business-entry-mode="small_business_growth"' in block
    assert 'data-aion-business-entry-mode="founder_build_idea"' in block
    assert 'data-aion-business-entry-mode="founder_generate_idea"' in block


def test_o20c_conversation_shell_has_terminal_and_mini_orb():
    text = APP.read_text(encoding="utf-8")
    assert "aion-o20c-conversation-shell" in text
    assert "aion-o20c-terminal" in text
    assert "aion-o20c-mini-orb" in text
    assert "panelHtmlO19I" in text
    assert "Business Twin Conversation" in text


def test_o20c_behaviour_persists_open_state_and_triggers_voice():
    text = APP.read_text(encoding="utf-8")
    assert 'aion.o20c.conversationOpen' in text
    assert 'aion.o20c.conversationMode' in text
    assert "startAionO19OOpeningFromBeginning" in text
    assert "data-aion-o19i-play-stage" in text
    assert "data-aion-o20c-reset-start" in text
