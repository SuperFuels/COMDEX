from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def renderer_block():
    text = read_app()
    start = text.index("function renderAionO25ETerminalOnlyVoiceConversation")
    end = text.index("function syncAionO25ETerminalOnlyVoiceConversation", start)
    return text[start:end]


def style_block():
    text = read_app()
    start = text.index("function installO25EStyles")
    end = text.index('document.head.appendChild(style)', start)
    return text[start:end]


def test_o25an_removes_large_terminal_heading_copy():
    block = renderer_block()
    assert "AION VOICE CONVERSATION" not in block
    assert "<h2>Business Foundation Conversation</h2>" not in block
    assert "aion-o25e-kicker" not in block


def test_o25an_uses_scaled_startup_orbital_visual():
    block = renderer_block()
    assert 'class="aion-o25e-mini-orbit' in block
    assert 'class="aion-o25e-mini-rings"' in block
    assert ">BOARDROOM<" in block
    assert ">BUSINESS TWIN<" in block
    assert ">PILOT<" in block
    assert ">COUNCIL<" in block
    assert 'class="aion-o25e-mini-core"' in block
    assert 'class="aion-o25e-mini-word">AION<' in block


def test_o25an_has_one_stateful_voice_button_only():
    block = renderer_block()
    assert block.count('data-aion-o25e-talk-toggle="true"') == 1
    assert "data-aion-o25e-stop-talking" not in block
    assert '${recording ? "Stop talking" : "Reply to AION"}' in block
    assert 'class="aion-o25e-talk ${recording ? "is-recording" : ""}"' in block


def test_o25an_terminal_is_full_height_borderless_with_fixed_footer():
    block = style_block()
    assert "height: 100vh;" in block
    assert "border: 0;" in block
    assert "border-radius: 0;" in block
    assert "box-shadow: none;" in block
    assert ".aion-o25e-footer" in block
    assert "position: sticky;" in block
    assert "bottom: 0;" in block


def test_o25an_preserves_transcript_and_typed_fallback():
    block = renderer_block()
    assert 'data-aion-o25e-transcript-log="true"' in block
    assert 'data-aion-o25e-typed-form="true"' in block
    assert 'data-aion-o25e-typed-input="true"' in block
    assert '<button type="submit">Send</button>' in block
