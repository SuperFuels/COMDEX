from __future__ import annotations

from backend.modules.workflow_capsules.connectors.providers.gmail_connector import (
    GMAIL_VAULT_HANDLE,
    GmailWorkflowConnector,
)
from backend.modules.workflow_capsules.connectors.providers.gmail_local_node_bridge import (
    LocalNodeGmailClientBridge,
)


class FakeLocalNodeRuntime:
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
            "draft_id": "draft-live-001",
            "message_id": "message-live-001",
            "thread_id": thread_id or "thread-live-001",
            "to": to,
            "subject": subject,
            "raw": "must-not-leak",
            "access_token": "must-not-leak",
        }


def test_gmail_provider_live_draft_requires_vault() -> None:
    connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    result = connector.create_draft(
        to="customer@example.com",
        subject="Re: Quote",
        body="Draft body",
        available_vault_requirements=[],
        live=True,
    )

    assert result.ok is False
    assert result.status == "blocked_missing_vault"
    assert result.errors == [f"missing_vault_requirement:{GMAIL_VAULT_HANDLE}"]


def test_gmail_provider_live_draft_requires_client_bridge() -> None:
    connector = GmailWorkflowConnector()

    result = connector.create_draft(
        to="customer@example.com",
        subject="Re: Quote",
        body="Draft body",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    )

    assert result.ok is False
    assert result.status == "blocked_live_draft_client_missing"
    assert "gmail_live_draft_client_missing" in result.errors


def test_gmail_provider_live_draft_uses_local_node_bridge_and_never_sends() -> None:
    connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    result = connector.create_draft(
        to="customer@example.com",
        subject="Re: Quote",
        body="Draft body",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    ).to_dict()

    assert result["ok"] is True
    assert result["status"] == "gmail_draft_created"
    assert result["payload"]["sent"] is False
    assert result["payload"]["must_not_send"] is True

    bridge_result = result["payload"]["bridge_result"]
    assert bridge_result["payload"]["draft_id"] == "draft-live-001"
    assert bridge_result["payload"]["sent"] is False
    assert bridge_result["payload"]["must_not_send"] is True
    assert bridge_result["payload"]["raw"] == "<redacted>"
    assert bridge_result["payload"]["access_token"] == "<redacted>"


def test_gmail_provider_capability_marks_live_draft_supported_but_send_not_supported() -> None:
    connector = GmailWorkflowConnector()
    caps = {c.action: c for c in connector.capabilities()}

    assert caps["read_message"].live_supported is True
    assert caps["create_draft"].live_supported is True
    assert caps["send_message"].live_supported is False
