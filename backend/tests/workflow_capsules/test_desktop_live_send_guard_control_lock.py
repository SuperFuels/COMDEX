from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def test_vault_live_send_control_exists_but_only_records_request() -> None:
    text = APP_JS.read_text()

    assert 'data-aion-vault-request-live-send="true"' in text
    assert "installAionVaultLiveSendRequestGuard" in text
    assert "window.__aionGmailLiveSendRequested = true" in text
    assert "aion.gmail.live_send_guard" in text

    assert "liveRunEnabled: false" in text
    assert "gmail_send_enabled: false" in text
    assert "gmail_reply_enabled: false" in text
    assert "gmail_send_draft_enabled: false" in text

    assert "AION can create approved Gmail drafts only" in text
    assert "it cannot send, reply, send drafts, or delete emails" in text


def test_live_send_guard_does_not_enable_live_execution_flags() -> None:
    text = APP_JS.read_text()

    forbidden_assignments = [
        "live_execute_enabled: true",
        "gmail_send_enabled: true",
        "gmail_reply_enabled: true",
        "gmail_send_draft_enabled: true",
        "live_send_enabled: true",
    ]

    for forbidden in forbidden_assignments:
        assert forbidden not in text
