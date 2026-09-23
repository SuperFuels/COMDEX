from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def test_o25h_single_authority_is_o25aj_now():
    text = read_app()
    assert "BEGIN AION O25AJ REAL VOICE TURN STATE BRIDGE LOCK" in text
    assert "BEGIN AION O25AH TERMINAL OPENING SCRIPT CLEAN LOCK" not in text
    assert "window.__aionO25AHCanonicalOpening" not in text


def test_o25h_removes_wrong_combined_prompt_from_voice_route():
    text = read_app()
    assert "What are you looking to achieve? Before we start, what should I call you?" not in text
    assert 'const AION_O25AJ_OPENING = "Before we start, what should I call you?";' in text


def test_o25h_cloud_voice_warning_is_hidden_from_visible_selected_terminal_markup():
    text = read_app()
    terminal_start = text.index("function renderAionO25ETerminalOnlyVoiceConversation")
    terminal_end = text.index("function syncAionO25ETerminalOnlyVoiceConversation", terminal_start)
    block = text[terminal_start:terminal_end]
    assert "Cloud voice" not in block
    assert "ElevenLabs credits" not in block


def test_o25h_aion_turns_render_as_aion_not_you_in_selected_terminal():
    text = read_app()
    start = text.index("BEGIN AION O25AJ REAL VOICE TURN STATE BRIDGE LOCK")
    block = text[start:]
    assert 'speaker: "AION"' in block
    assert 'speaker: "You"' in block
    assert "aion_intro_as_user_visible" in block
    assert "looksAion" in block


def test_o25h_legacy_browser_speech_runtime_disabled():
    text = read_app()
    assert "Browser SpeechRecognition runtime calls are disabled" in text
    assert "window.__aionO22FBrowserSpeechRuntimeDisabled = true" in text


def test_o25h_preview_safety_still_locked():
    text = read_app()
    assert "external_actions_allowed: false" in text
    assert "live_execution_allowed: false" in text
