from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o19n_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19N OPENING SPEECH CAPTURE VISUALIZER LOCK" in text
    assert "O19N opening speech capture visualizer installed" in text
    assert "__debugAionO19NOpeningSpeechCaptureVisualizer" in text


def test_o19n_click_aion_starts_opening_voice_sequence():
    text = APP.read_text(encoding="utf-8")
    assert "startAionO19NOpeningSequence" in text
    assert "Welcome to Tessaris" in text
    assert "playCurrentPrompt" in text
    assert "speakText" in text
    assert "onwK4e9ZLuTAKqWW03F9" in text


def test_o19n_captures_typed_answer_and_name():
    text = APP.read_text(encoding="utf-8")
    assert "captureAionO19NUserAnswer" in text
    assert "handleUserAnswer" in text
    assert "data-aion-o19i-save-reply" in text
    assert "data-aion-o19i-user-reply" in text
    assert "state.user_name" in text
    assert "startup_choice" in text


def test_o19n_voice_visualizer_exists():
    text = APP.read_text(encoding="utf-8")
    assert "aion-o19n-voice-bars" in text
    assert "aion-o19n-speaking" in text
    assert "@keyframes aionO19NVoiceBars" in text
    assert "setSpeaking(true)" in text
    assert "setSpeaking(false)" in text
