from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop" / "mac" / "src" / "app.js"


def read_app():
    return APP.read_text(encoding="utf-8")


def test_o25x_selected_terminal_design_is_the_o25e_card_design():
    text = read_app()

    assert "aion-o25e-voice-terminal" in text
    assert 'data-aion-o25e-voice-terminal-only="true"' in text
    assert "AION VOICE CONVERSATION" in text
    assert "Business Foundation Conversation" in text
    assert "Reply to AION" in text
    assert "Stop talking" in text
    assert "Local voice runtime · transcript captured into Business Foundation draft · preview only" in text


def test_o25x_wrong_o25w_terminal_design_is_not_active():
    text = read_app()

    assert "aion-o25w-current-terminal" not in text
    assert "data-aion-o25w-current-terminal" not in text
    assert "data-aion-o25w-big-graphic-startup" not in text


def test_o25x_selected_design_keeps_big_graphic_startup_available():
    text = read_app()

    assert "aion-o20b-orbit" in text
    assert "aion-o20b-rings" in text
    assert "What are we building?" in text
    assert "I have a business" in text
