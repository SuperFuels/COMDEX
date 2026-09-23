from pathlib import Path

DOC = Path("docs/rfc/aion_agent_channels_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_agent_channels_lock_doc_exists():
    assert DOC.exists()
    assert "AION Agent Communication Channels v0.1 Lock" in _text()


def test_agent_channels_lock_doc_lists_reserved_channels():
    text = _text()
    for term in [
        "agent\\_email",
        "agent\\_phone",
        "whatsapp",
        "embedded\\_chat",
        "supplier\\_email",
        "booking\\_inbox",
    ]:
        assert term in text


def test_agent_channels_lock_doc_lists_core_fields():
    text = _text()
    for term in [
        "message\\_id",
        "business\\_id",
        "channel\\_key",
        "raw\\_subject",
        "raw\\_body",
        "sender\\_ref",
        "job\\_id",
        "message\\_hash",
    ]:
        assert term in text


def test_agent_channels_lock_doc_states_safety_flags():
    text = _text()
    for term in [
        "would\\_send\\_email = false",
        "would\\_send\\_whatsapp = false",
        "would\\_call\\_phone\\_provider = false",
        "would\\_mutate\\_job\\_timeline = false",
        "would\\_create\\_external\\_side\\_effect = false",
    ]:
        assert term in text


def test_agent_channels_lock_doc_states_no_side_effects():
    text = _text()
    assert "MUST NOT" in text
    assert "send email" in text
    assert "send WhatsApp messages" in text
    assert "call a phone provider" in text
    assert "mutate an active job timeline" in text
    assert "expose a public route" in text


def test_agent_channels_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
