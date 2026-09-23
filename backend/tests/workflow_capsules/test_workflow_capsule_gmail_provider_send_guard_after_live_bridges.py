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
        return [
            {
                "id": "msg-live-001",
                "thread_id": "thread-live-001",
                "from": "customer@example.com",
                "subject": "Live read test",
                "body": "Sanitized body",
                "access_token": "must-not-leak",
            }
        ]

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
            "to": to,
            "subject": subject,
            "raw": "must-not-leak",
        }


def test_live_send_still_requires_approval_even_when_read_and_draft_are_bridged() -> None:
    connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    result = connector.send_message(
        to="customer@example.com",
        subject="Re: Quote",
        body="Body",
        approval={"status": "pending"},
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    )

    assert result.ok is False
    assert result.status == "blocked_missing_approval"
    assert result.errors == ["approval_not_approved"]


def test_live_send_still_requires_env_guard_even_when_read_and_draft_are_bridged(monkeypatch) -> None:
    monkeypatch.delenv(LIVE_GMAIL_ENV_GUARD, raising=False)

    connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    result = connector.send_message(
        to="customer@example.com",
        subject="Re: Quote",
        body="Body",
        approval={"status": "approved"},
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    )

    assert result.ok is False
    assert result.status == "blocked_live_env_guard"
    assert result.errors == [f"missing_env_guard:{LIVE_GMAIL_ENV_GUARD}=1"]


def test_live_send_still_not_implemented_even_with_vault_approval_env_and_bridge(monkeypatch) -> None:
    monkeypatch.setenv(LIVE_GMAIL_ENV_GUARD, "1")

    connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    result = connector.send_message(
        to="customer@example.com",
        subject="Re: Quote",
        body="Body",
        approval={"status": "approved"},
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    ).to_dict()

    assert result["ok"] is False
    assert result["status"] == "blocked_live_connector_not_implemented"
    assert "gmail_live_send_not_implemented" in result["errors"]
    assert result["payload"]["message"] == (
        "Live Gmail send guard passed, but real Gmail send is not implemented yet."
    )


def test_non_live_send_remains_simulated_ready_and_must_not_send() -> None:
    connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    result = connector.send_message(
        to="customer@example.com",
        subject="Re: Quote",
        body="Body",
        approval={"status": "approved"},
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=False,
    ).to_dict()

    assert result["ok"] is True
    assert result["status"] == "simulated_external_write_ready"
    assert result["payload"]["ready"] is True
    assert result["payload"]["must_not_send"] is True
