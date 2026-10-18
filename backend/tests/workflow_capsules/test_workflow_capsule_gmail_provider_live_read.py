from __future__ import annotations

from backend.modules.workflow_capsules.connectors.providers.gmail_connector import (
    GMAIL_VAULT_HANDLE,
    GmailWorkflowConnector,
)
from backend.modules.workflow_capsules.connectors.providers.gmail_local_node_bridge import (
    LocalNodeGmailClientBridge,
)


class FakeLocalNodeRuntime:
    def _fetch_gmail_unread_messages(self, *, query: str, max_results: int):
        return [
            {
                "id": "msg-live-001",
                "thread_id": "thread-live-001",
                "from": "customer@example.com",
                "subject": "Live read test",
                "body": "This is a sanitized live read result.",
                "access_token": "must-not-leak",
                "refresh_token": "must-not-leak",
            }
        ]


def test_gmail_provider_live_read_requires_vault() -> None:
    connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    result = connector.read_message(
        message_id="msg-live-001",
        available_vault_requirements=[],
        live=True,
    )

    assert result.ok is False
    assert result.status == "blocked_missing_vault"
    assert result.errors == [f"missing_vault_requirement:{GMAIL_VAULT_HANDLE}"]


def test_gmail_provider_live_read_requires_client_bridge() -> None:
    connector = GmailWorkflowConnector()

    result = connector.read_message(
        message_id="msg-live-001",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    )

    assert result.ok is False
    assert result.status == "blocked_live_read_client_missing"
    assert "gmail_live_read_client_missing" in result.errors


def test_gmail_provider_live_read_uses_local_node_bridge_and_sanitizes_tokens() -> None:
    connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    result = connector.read_message(
        message_id="msg-live-001",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    ).to_dict()

    assert result["ok"] is True
    assert result["status"] == "gmail_read_completed"

    bridge_result = result["payload"]["bridge_result"]
    assert bridge_result["payload"]["count"] == 1

    msg = bridge_result["payload"]["messages"][0]
    assert msg["id"] == "msg-live-001"
    assert msg["access_token"] == "<redacted>"
    assert msg["refresh_token"] == "<redacted>"


def test_gmail_provider_capability_marks_live_read_supported_but_send_not_supported() -> None:
    connector = GmailWorkflowConnector()
    caps = {c.action: c for c in connector.capabilities()}

    assert caps["read_message"].live_supported is True
    assert caps["send_message"].live_supported is False
