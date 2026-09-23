from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def renderer_block() -> str:
    text = read_app()
    start = text.index(
        "function renderAionO25ETerminalOnlyVoiceConversation"
    )
    end = text.index(
        "function syncAionO25ETerminalOnlyVoiceConversation",
        start,
    )
    return text[start:end]


def test_o25ap_mic_state_updates_visible_control():
    text = read_app()

    assert "aion:o21e-mic-state-changed" in text
    assert "data-aion-o25e-talk-toggle" in text
    assert "label.textContent = recording" in text
    assert "button.classList.toggle" in text


def test_o25ap_button_uses_real_recording_state():
    block = renderer_block()

    assert (
        'data-aion-o25e-talk-state="${recording ? "listening" : "idle"}"'
        in block
    )
    assert 'data-aion-o25e-talk-label="true"' in block
    assert '${recording ? "Stop talking" : "Reply to AION"}' in block


def test_o25ap_activity_display_has_fourteen_bars():
    block = renderer_block()

    assert 'Array.from({ length: 14 }' in block


def test_o25ap_listening_button_has_distinct_colour():
    text = read_app()

    assert (
        '.aion-o25e-talk[data-aion-o25e-talk-state="listening"]'
        in text
    )
    assert "background: #0f766e !important;" in text


def test_o25ap_activity_bar_uses_full_width_grid():
    text = read_app()

    assert "repeat(14, minmax(6px, 1fr))" in text
    assert (
        ".aion-o25e-voice-bar.is-active span:nth-child(14)"
        in text
    )
