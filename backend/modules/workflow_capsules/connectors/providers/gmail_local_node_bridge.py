from __future__ import annotations

"""
Gmail Local Node Bridge - AION Workflow Capsules v1
──────────────────────────────────────────────────

Thin bridge over the existing LocalNodeRuntime Gmail connector code.

This does not own credentials.
This does not store tokens.
This does not expose raw token payloads.

It exists so workflow connector providers can call a small, stable Gmail client
surface instead of reaching into LocalNodeRuntime internals directly.

Existing lower path:
  LocalNodeRuntime
    -> ConnectorRegistryStore
    -> Gmail OAuth token refresh
    -> Gmail API GET/POST helpers
    -> Gmail read / draft creation

Security note:
  The workflow connector layer should only receive sanitized results.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GmailBridgeResult:
    ok: bool
    action: str
    status: str

    payload: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    schema_version: str = "aion.gmail_local_node_bridge_result.v1"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["payload"] = _sanitize_payload(data.get("payload") or {})
        return data


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        clean: Dict[str, Any] = {}
        blocked = {
            "access_token",
            "refresh_token",
            "id_token",
            "client_secret",
            "password",
            "authorization",
            "raw",
        }
        for k, v in value.items():
            key = str(k)
            if key.lower() in blocked:
                clean[key] = "<redacted>"
            else:
                clean[key] = _sanitize_payload(v)
        return clean

    if isinstance(value, list):
        return [_sanitize_payload(v) for v in value]

    return value


class LocalNodeGmailClientBridge:
    """
    Stable Gmail client wrapper over LocalNodeRuntime.

    Required runtime methods:
      - get_gmail_connector_health()
      - _fetch_gmail_unread_messages(query=..., max_results=...)
      - _create_gmail_draft(to=..., subject=..., body=..., cc=..., bcc=..., thread_id=...)
    """

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime

    def health(self) -> GmailBridgeResult:
        try:
            if not hasattr(self.runtime, "get_gmail_connector_health"):
                return GmailBridgeResult(
                    ok=False,
                    action="health",
                    status="runtime_missing_health_method",
                    errors=["runtime_missing:get_gmail_connector_health"],
                )

            result = self.runtime.get_gmail_connector_health()
            result = result if isinstance(result, dict) else {}

            return GmailBridgeResult(
                ok=bool(result.get("ok", True)),
                action="health",
                status=str(result.get("connector_health") or result.get("status") or "unknown"),
                payload=result,
            )
        except Exception as exc:
            return GmailBridgeResult(
                ok=False,
                action="health",
                status="exception",
                errors=[f"{type(exc).__name__}: {exc}"],
            )

    def read_messages(
        self,
        *,
        query: str = "in:inbox is:unread",
        max_results: int = 10,
    ) -> GmailBridgeResult:
        try:
            if not hasattr(self.runtime, "_fetch_gmail_unread_messages"):
                return GmailBridgeResult(
                    ok=False,
                    action="read_messages",
                    status="runtime_missing_read_method",
                    errors=["runtime_missing:_fetch_gmail_unread_messages"],
                )

            messages = self.runtime._fetch_gmail_unread_messages(
                query=query or "in:inbox is:unread",
                max_results=max(1, min(int(max_results or 10), 25)),
            )

            safe_messages = [
                _sanitize_payload(m)
                for m in list(messages or [])
                if isinstance(m, dict)
            ]

            return GmailBridgeResult(
                ok=True,
                action="read_messages",
                status="gmail_read_completed",
                payload={
                    "messages": safe_messages,
                    "count": len(safe_messages),
                    "query": query or "in:inbox is:unread",
                },
            )
        except Exception as exc:
            return GmailBridgeResult(
                ok=False,
                action="read_messages",
                status="exception",
                errors=[f"{type(exc).__name__}: {exc}"],
            )

    def create_draft(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        thread_id: str = "",
    ) -> GmailBridgeResult:
        try:
            if not hasattr(self.runtime, "_create_gmail_draft"):
                return GmailBridgeResult(
                    ok=False,
                    action="create_draft",
                    status="runtime_missing_draft_method",
                    errors=["runtime_missing:_create_gmail_draft"],
                )

            result = self.runtime._create_gmail_draft(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                thread_id=thread_id,
            )

            result = result if isinstance(result, dict) else {}

            return GmailBridgeResult(
                ok=bool(result.get("ok", True)),
                action="create_draft",
                status="gmail_draft_created" if result.get("created") else "gmail_draft_result",
                payload={
                    **_sanitize_payload(result),
                    "sent": False,
                    "must_not_send": True,
                },
            )
        except Exception as exc:
            return GmailBridgeResult(
                ok=False,
                action="create_draft",
                status="exception",
                errors=[f"{type(exc).__name__}: {exc}"],
            )
