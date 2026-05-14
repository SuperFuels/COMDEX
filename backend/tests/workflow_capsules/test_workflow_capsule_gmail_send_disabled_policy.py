from __future__ import annotations

from backend.modules.workflow_capsules.connectors.providers.gmail_connector import (
    GMAIL_VAULT_HANDLE,
    LIVE_GMAIL_ENV_GUARD,
    GmailWorkflowConnector,
)
from backend.modules.workflow_capsules.connectors.providers.gmail_local_node_bridge import (
    LocalNodeGmailClientBridge,
)


class FakeLocalNodeRuntime:
    def _fetch_gmail_unread_messages(self, *, query: str, max_results: int):
        return [{"id": "msg-001", "subject": "Test"}]

    def _create_gmail_draft(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        thread_id: str = "",
    ):
        return {
            "ok": True,
            "created": True,
            "sent": False,
            "draft_id": "draft-001",
            "to": to,
            "subject": subject,
        }


def test_gmail_live_send_is_product_disabled_even_after_read_and_draft_live_paths(monkeypatch) -> None:
    """
    Product decision lock:

    Gmail read and Gmail draft may be live-bridged through LocalNodeRuntime.
    Gmail send remains disabled as a product/runtime policy until a future
    explicit send feature is designed, audited, and tested.
    """
    monkeypatch.setenv(LIVE_GMAIL_ENV_GUARD, "1")

    connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    read = connector.read_message(
        message_id="msg-001",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    )

    draft = connector.create_draft(
        to="customer@example.com",
        subject="Re: Test",
        body="Draft only",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    )

    send = connector.send_message(
        to="customer@example.com",
        subject="Re: Test",
        body="Should not send",
        approval={"status": "approved"},
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    )

    assert read.ok is True
    assert draft.ok is True

    assert send.ok is False
    assert send.status == "blocked_live_connector_not_implemented"
    assert "gmail_live_send_not_implemented" in send.errors


def test_gmail_send_capability_remains_live_unsupported() -> None:
    connector = GmailWorkflowConnector()
    caps = {c.action: c for c in connector.capabilities()}

    assert caps["read_message"].live_supported is True
    assert caps["create_draft"].live_supported is True
    assert caps["send_message"].live_supported is False
    assert caps["send_message"].requires_approval is True
    assert caps["send_message"].requires_vault == [GMAIL_VAULT_HANDLE]
    assert caps["send_message"].env_guards == [LIVE_GMAIL_ENV_GUARD]
