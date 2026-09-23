from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass(slots=True)
class MicrosoftGraphMailResult:
    ok: bool
    action: str
    status_code: int
    latency_ms: int
    provider_request_id: str = ""
    error_code: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class MicrosoftGraphMailAdapter:
    """Bounded Microsoft Graph mail adapter.

    OAuth acquisition and refresh remain Vault responsibilities.  This adapter
    receives a short-lived access token, never persists it, and only performs an
    action after its caller has passed the policy/approval gate.
    """

    def __init__(self, *, access_token: str, timeout_s: int = 30) -> None:
        self.access_token = access_token.strip()
        self.timeout_s = timeout_s

    def is_configured(self) -> bool:
        return bool(self.access_token)

    def send_email(
        self,
        *,
        to_emails: Iterable[str],
        subject: str,
        body_text: str,
        cc_emails: Iterable[str] = (),
        save_to_sent_items: bool = True,
    ) -> MicrosoftGraphMailResult:
        return self._write_message(
            action="send_email",
            endpoint="https://graph.microsoft.com/v1.0/me/sendMail",
            to_emails=to_emails,
            cc_emails=cc_emails,
            subject=subject,
            body_text=body_text,
            save_to_sent_items=save_to_sent_items,
        )

    def create_draft(
        self,
        *,
        to_emails: Iterable[str],
        subject: str,
        body_text: str,
        cc_emails: Iterable[str] = (),
    ) -> MicrosoftGraphMailResult:
        return self._write_message(
            action="create_draft",
            endpoint="https://graph.microsoft.com/v1.0/me/messages",
            to_emails=to_emails,
            cc_emails=cc_emails,
            subject=subject,
            body_text=body_text,
        )

    def _write_message(
        self,
        *,
        action: str,
        endpoint: str,
        to_emails: Iterable[str],
        cc_emails: Iterable[str],
        subject: str,
        body_text: str,
        save_to_sent_items: bool = True,
    ) -> MicrosoftGraphMailResult:
        if not self.is_configured():
            return MicrosoftGraphMailResult(False, action, 0, 0, error_code="missing_microsoft_graph_access_token")
        recipients = self._recipients(to_emails)
        if not recipients:
            return MicrosoftGraphMailResult(False, action, 0, 0, error_code="missing_to_emails")

        try:
            import requests
        except Exception as exc:
            return MicrosoftGraphMailResult(False, action, 0, 0, error_code=f"requests_import_failed:{exc}")

        message = {
            "subject": str(subject).strip(),
            "body": {"contentType": "Text", "content": str(body_text)},
            "toRecipients": recipients,
            "ccRecipients": self._recipients(cc_emails),
        }
        payload: Dict[str, Any] = {"message": message, "saveToSentItems": save_to_sent_items} if action == "send_email" else message
        started = time.time()
        try:
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_s,
            )
            latency_ms = int((time.time() - started) * 1000)
            request_id = response.headers.get("request-id") or response.headers.get("client-request-id") or ""
            if response.status_code >= 400:
                return MicrosoftGraphMailResult(
                    False,
                    action,
                    response.status_code,
                    latency_ms,
                    provider_request_id=request_id,
                    error_code=f"microsoft_graph_mail_failed:{response.status_code}",
                    raw={"response_text": response.text[:1000]},
                )
            body: Dict[str, Any] = {}
            if response.content:
                try:
                    body = response.json()
                except Exception:
                    body = {}
            return MicrosoftGraphMailResult(
                True,
                action,
                response.status_code,
                latency_ms,
                provider_request_id=request_id or str(body.get("id") or ""),
                raw={"message_id": body.get("id"), "accepted": response.status_code == 202},
            )
        except Exception as exc:
            return MicrosoftGraphMailResult(False, action, 0, int((time.time() - started) * 1000), error_code=f"microsoft_graph_request_failed:{exc}")

    @staticmethod
    def _recipients(values: Iterable[str]) -> list[Dict[str, Dict[str, str]]]:
        return [
            {"emailAddress": {"address": str(value).strip()}}
            for value in values
            if str(value).strip()
        ]

