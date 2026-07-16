from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def o25aj_block() -> str:
    text = read_app()
    start = text.index(
        "BEGIN AION O25AJ REAL VOICE TURN STATE BRIDGE LOCK"
    )
    end = text.index(
        "END AION O25AJ REAL VOICE TURN STATE BRIDGE LOCK",
        start,
    )
    return text[start:end]


def test_o25aq_has_authoritative_speaking_visual_helper():
    block = o25aj_block()
    assert "function setAionSpeakingVisualO25AQ" in block
    assert 'state.status = speaking ? "speaking" : nextStatus' in block


def test_o25aq_uses_actual_audio_playback_events():
    block = o25aj_block()
    assert "audio.onplay = markPlaybackStarted" in block
    assert "audio.onplaying = markPlaybackStarted" in block
    assert 'finishPlayback("idle")' in block


def test_o25aq_does_not_mark_speaking_during_tts_generation():
    block = o25aj_block()
    assert 'state.status = "loading_voice"' in block
    assert 'setAionSpeakingVisualO25AQ(false, "loading_voice")' in block


def test_o25aq_speaking_bar_has_distinct_teal_visual():
    block = o25aj_block()
    assert "aion-o25aq-real-audio-visual-style" in block
    assert 'data-aion-o25e-voice-activity="speaking"' in block
    assert "background: #14b8a6 !important;" in block


def test_o25aq_clears_visual_on_audio_error():
    block = o25aj_block()
    assert '"audio_playback_error"' in block
    assert '"voice_error"' in block
