from __future__ import annotations

from backend.modules.workflow_capsules.connectors.providers.gmail_local_node_bridge import (
    LocalNodeGmailClientBridge,
)


class FakeLocalNodeRuntime:
    def get_gmail_connector_health(self):
        return {
            "ok": True,
            "provider": "gmail",
            "auth_status": "connected",
            "connector_health": "available",
            "access_token": "must-not-leak",
        }

    def _fetch_gmail_unread_messages(self, *, query: str, max_results: int):
        return [
            {
                "id": "msg-001",
                "thread_id": "thread-001",
                "from": "customer@example.com",
                "subject": "Need a quote",
                "body": "Can you help?",
                "access_token": "must-not-leak",
                "refresh_token": "must-not-leak",
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
            "draft_id": "draft-001",
            "message_id": "message-001",
            "thread_id": thread_id or "thread-001",
            "to": to,
            "subject": subject,
            "raw": "must-not-leak",
            "access_token": "must-not-leak",
        }


def test_gmail_local_node_bridge_health_sanitizes_secret_fields() -> None:
    bridge = LocalNodeGmailClientBridge(FakeLocalNodeRuntime())

    result = bridge.health().to_dict()

    assert result["ok"] is True
    assert result["status"] == "available"
    assert result["payload"]["access_token"] == "<redacted>"


def test_gmail_local_node_bridge_read_messages_sanitizes_tokens() -> None:
    bridge = LocalNodeGmailClientBridge(FakeLocalNodeRuntime())

    result = bridge.read_messages(query="from:customer@example.com", max_results=5).to_dict()

    assert result["ok"] is True
    assert result["status"] == "gmail_read_completed"
    assert result["payload"]["count"] == 1

    msg = result["payload"]["messages"][0]
    assert msg["id"] == "msg-001"
    assert msg["access_token"] == "<redacted>"
    assert msg["refresh_token"] == "<redacted>"


def test_gmail_local_node_bridge_create_draft_sanitizes_and_never_marks_sent() -> None:
    bridge = LocalNodeGmailClientBridge(FakeLocalNodeRuntime())

    result = bridge.create_draft(
        to="customer@example.com",
        subject="Re: Need a quote",
        body="Draft body",
        thread_id="thread-001",
    ).to_dict()

    assert result["ok"] is True
    assert result["status"] == "gmail_draft_created"
    assert result["payload"]["draft_id"] == "draft-001"
    assert result["payload"]["sent"] is False
    assert result["payload"]["must_not_send"] is True
    assert result["payload"]["raw"] == "<redacted>"
    assert result["payload"]["access_token"] == "<redacted>"


def test_gmail_local_node_bridge_missing_runtime_methods_fail_safely() -> None:
    bridge = LocalNodeGmailClientBridge(object())

    read = bridge.read_messages().to_dict()
    draft = bridge.create_draft(
        to="customer@example.com",
        subject="Subject",
        body="Body",
    ).to_dict()

    assert read["ok"] is False
    assert read["status"] == "runtime_missing_read_method"
    assert draft["ok"] is False
    assert draft["status"] == "runtime_missing_draft_method"
