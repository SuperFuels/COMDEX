from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def test_o25am_direct_paint_helper_exists_and_is_called_before_sync():
    text = read_app()
    assert "function paintRowO25AJ(item)" in text
    assert "paintRowO25AJ(item);" in text
    assert 'data-aion-o25aj-row-id' in text
    assert "log.appendChild(row)" in text


def test_o25am_zero_delay_sync_is_not_only_settimeout_deferred():
    text = read_app()
    start = text.index("function syncTerminalO25AJ(delay = 0)")
    end = text.index("async function speakLocalO25AJ", start)
    block = text[start:end]
    assert "if (!delay)" in block
    assert "run();" in block
    assert "requestAnimationFrame(run)" in block
    assert "window.setTimeout(run, delay)" in block


def test_o25am_full_terminal_sync_scrolls_to_bottom_after_render():
    text = read_app()
    start = text.index("function syncAionO25ETerminalOnlyVoiceConversation")
    end = text.index("async function handleO25ETalkToggle", start)
    block = text[start:end]
    assert "terminal.innerHTML = renderAionO25ETerminalOnlyVoiceConversation();" in block
    assert "transcript.scrollTop = transcript.scrollHeight" in block
    assert "requestAnimationFrame" in block


def test_o25am_debug_exposes_paint_error():
    text = read_app()
    assert "__aionO25AJLastPaintError" in text
    assert "last_paint_error" in text
