from pathlib import Path

APP = Path("desktop/mac/src/app.js")

CANONICAL = (
    "Welcome to AION. I can help map your business, build your Business Foundation, "
    "create your Business Map, activate the Boardroom, and route deeper discovery "
    "to the right department pilots. What are you looking to achieve? Before we start, "
    "what should I call you?"
)


def read_app():
    return APP.read_text(encoding="utf-8")


def test_terminal_has_single_canonical_opening_script():
    text = read_app()
    assert CANONICAL in text
    assert "Are we working with an existing business, a new business idea, or a limited-context task?" not in text


def test_terminal_does_not_seed_aion_intro_as_user_turn():
    text = read_app()
    assert "YOU\\nWelcome to AION" not in text
    assert "You · local STT\\nWelcome to AION" not in text
    assert "speaker: \"user\",\\n      text: \"Welcome to AION" not in text
    assert "speaker: 'user',\\n      text: 'Welcome to AION" not in text


def test_o25ah_echo_guard_installed():
    text = read_app()
    assert "BEGIN AION O25AH TERMINAL OPENING SCRIPT CLEAN LOCK" in text
    assert "__aionO25AHCanonicalOpening" in text
    assert "BlockedAionEchoAsUser" in text or "BlockedAionEcho" in text
