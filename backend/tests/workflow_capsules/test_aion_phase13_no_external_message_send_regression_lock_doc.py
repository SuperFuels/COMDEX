from pathlib import Path


DOC = Path("docs/rfc/aion_phase13_no_external_message_send_regression_lock.tex")


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_phase13_no_external_message_doc_exists():
    assert DOC.exists()


def test_phase13_no_external_message_doc_status_present():
    text = _text()
    assert "Phase 13E --- No-External-Message-Send Regression v0" in text
    assert "Status:" in text


def test_phase13_no_external_message_doc_lists_locked_flags():
    text = _text()

    for term in [
        "would\\_send\\_external\\_messages = false",
        "approval\\_can\\_send\\_external\\_messages = false",
        "preview\\_only = true",
        "human\\_review\\_required = true",
    ]:
        assert term in text


def test_phase13_no_external_message_doc_lists_forbidden_couplings():
    text = _text()

    for term in [
        "send\\_email",
        "send\\_message",
        "send\\_whatsapp",
        "send\\_sms",
        "smtplib",
        "twilio",
        "sendgrid",
        "mailgun",
        "postmark",
        "external\\_message\\_provider",
        "live\\_message\\_send",
    ]:
        assert term in text


def test_phase13_no_external_message_doc_states_no_frontend_smoke_test():
    text = _text()
    assert "does not create a new frontend visual surface" in text
    assert "No new manual frontend smoke test is required" in text


def test_phase13_no_external_message_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_phase13_no_external_message_doc_has_validation_commands():
    text = _text()
    assert "test_aion_phase13_no_external_message_send_regression_lock.py" in text
    assert "scripts/run_goal_engine_focused_lock_suite.sh" in text
    assert "python -m compileall backend/modules/aion_gateway" in text
