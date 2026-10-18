from __future__ import annotations

import base64
from datetime import datetime, timezone
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
from urllib.parse import quote


@dataclass(slots=True)
class MicrosoftGraphMailResult:
    ok: bool
    action: str
    status_code: int
    latency_ms: int
    provider_request_id: str = ""
    error_code: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class MicrosoftGraphMessageTraceResult:
    ok: bool
    found: bool
    status_code: int
    latency_ms: int
    trace_id: str = ""
    internet_message_id: str = ""
    provider_status: str = ""
    observed_at: str = ""
    error_code: Optional[str] = None


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
        attachments: Iterable[Dict[str, str]] = (),
        save_to_sent_items: bool = True,
    ) -> MicrosoftGraphMailResult:
        return self._write_message(
            action="send_email",
            endpoint="https://graph.microsoft.com/v1.0/me/sendMail",
            to_emails=to_emails,
            cc_emails=cc_emails,
            subject=subject,
            body_text=body_text,
            attachments=attachments,
            save_to_sent_items=save_to_sent_items,
        )

    def create_draft(
        self,
        *,
        to_emails: Iterable[str],
        subject: str,
        body_text: str,
        cc_emails: Iterable[str] = (),
        attachments: Iterable[Dict[str, str]] = (),
    ) -> MicrosoftGraphMailResult:
        return self._write_message(
            action="create_draft",
            endpoint="https://graph.microsoft.com/v1.0/me/messages",
            to_emails=to_emails,
            cc_emails=cc_emails,
            subject=subject,
            body_text=body_text,
            attachments=attachments,
        )

    def send_traceable_email(
        self,
        *,
        to_emails: Iterable[str],
        subject: str,
        body_text: str,
        tracking_id: str,
        cc_emails: Iterable[str] = (),
        attachments: Iterable[Dict[str, str]] = (),
    ) -> MicrosoftGraphMailResult:
        """Create and send a draft while retaining its Internet Message-ID.

        Graph ``sendMail`` returns only acceptance.  Creating the draft first is
        the documented way to retain an immutable message identifier and gives us
        the Internet Message-ID needed for an exact Exchange Message Trace query.
        """

        if not self.is_configured():
            return MicrosoftGraphMailResult(
                False, "send_traceable_email", 0, 0,
                error_code="missing_microsoft_graph_access_token",
            )
        recipients = self._recipients(to_emails)
        if not recipients:
            return MicrosoftGraphMailResult(
                False, "send_traceable_email", 0, 0, error_code="missing_to_emails",
            )
        tracking = str(tracking_id or "").strip()
        if not tracking or len(tracking) > 160:
            return MicrosoftGraphMailResult(
                False, "send_traceable_email", 0, 0,
                error_code="microsoft_graph_tracking_id_required",
            )
        try:
            files = self._attachments(attachments)
        except ValueError as exc:
            return MicrosoftGraphMailResult(
                False, "send_traceable_email", 0, 0, error_code=str(exc),
            )
        try:
            import requests
        except Exception as exc:
            return MicrosoftGraphMailResult(
                False, "send_traceable_email", 0, 0,
                error_code=f"requests_import_failed:{exc}",
            )

        message: Dict[str, Any] = {
            "subject": str(subject).strip(),
            "body": {"contentType": "Text", "content": str(body_text)},
            "toRecipients": recipients,
            "ccRecipients": self._recipients(cc_emails),
            "internetMessageHeaders": [{
                "name": "x-tessaris-delivery-id", "value": tracking,
            }],
        }
        if files:
            message["attachments"] = files
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Prefer": 'IdType="ImmutableId"',
        }
        started = time.time()
        try:
            draft_response = requests.post(
                "https://graph.microsoft.com/v1.0/me/messages",
                headers=headers,
                json=message,
                timeout=self.timeout_s,
            )
            latency_ms = int((time.time() - started) * 1000)
            if draft_response.status_code != 201:
                return MicrosoftGraphMailResult(
                    False, "send_traceable_email", draft_response.status_code,
                    latency_ms,
                    provider_request_id=(
                        draft_response.headers.get("request-id")
                        or draft_response.headers.get("client-request-id") or ""
                    ),
                    error_code=f"microsoft_graph_draft_failed:{draft_response.status_code}",
                    raw={"response_text": draft_response.text[:1000]},
                )
            try:
                draft = dict(draft_response.json() or {})
            except Exception:
                draft = {}
            draft_id = str(draft.get("id") or "").strip()
            internet_message_id = str(draft.get("internetMessageId") or "").strip()
            if not draft_id or not internet_message_id:
                return MicrosoftGraphMailResult(
                    False, "send_traceable_email", draft_response.status_code,
                    latency_ms,
                    error_code="microsoft_graph_traceable_identifiers_missing",
                )
            send_response = requests.post(
                f"https://graph.microsoft.com/v1.0/me/messages/{quote(draft_id, safe='')}/send",
                headers={**headers, "Content-Length": "0"},
                timeout=self.timeout_s,
            )
            latency_ms = int((time.time() - started) * 1000)
            send_request_id = (
                send_response.headers.get("request-id")
                or send_response.headers.get("client-request-id") or ""
            )
            if send_response.status_code != 202:
                return MicrosoftGraphMailResult(
                    False, "send_traceable_email", send_response.status_code,
                    latency_ms, provider_request_id=internet_message_id,
                    error_code=f"microsoft_graph_draft_send_failed:{send_response.status_code}",
                    raw={
                        "graph_message_id": draft_id,
                        "send_request_id": send_request_id,
                        "response_text": send_response.text[:1000],
                    },
                )
            return MicrosoftGraphMailResult(
                True, "send_traceable_email", 202, latency_ms,
                provider_request_id=internet_message_id,
                raw={
                    "graph_message_id": draft_id,
                    "internet_message_id": internet_message_id,
                    "send_request_id": send_request_id,
                    "accepted": True,
                },
            )
        except Exception as exc:
            return MicrosoftGraphMailResult(
                False, "send_traceable_email", 0,
                int((time.time() - started) * 1000),
                error_code=f"microsoft_graph_request_failed:{exc}",
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
        attachments: Iterable[Dict[str, str]],
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
        try:
            files = self._attachments(attachments)
        except ValueError as exc:
            return MicrosoftGraphMailResult(False, action, 0, 0, error_code=str(exc))
        if files:
            message["attachments"] = files
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

    @staticmethod
    def _attachments(values: Iterable[Dict[str, str]]) -> list[Dict[str, str]]:
        result: list[Dict[str, str]] = []
        total = 0
        for item in values:
            if len(result) >= 10:
                raise ValueError("microsoft_graph_too_many_attachments")
            name = str(item.get("name") or item.get("filename") or "").strip()[:240]
            content_type = str(item.get("content_type") or "application/octet-stream").strip()[:120]
            content = str(item.get("content_base64") or item.get("content") or "").strip()
            if not name or not content:
                raise ValueError("microsoft_graph_attachment_name_and_content_required")
            try:
                decoded = base64.b64decode(content, validate=True)
            except Exception as exc:
                raise ValueError("microsoft_graph_attachment_content_must_be_base64") from exc
            total += len(decoded)
            if total > 10_000_000:
                raise ValueError("microsoft_graph_attachments_too_large")
            result.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": name,
                "contentType": content_type,
                "contentBytes": content,
            })
        return result


class MicrosoftGraphMessageTraceAdapter:
    """Read bounded Exchange Online message-trace delivery evidence."""

    ENDPOINT = "https://graph.microsoft.com/v1.0/admin/exchange/tracing/messageTraces"

    def __init__(self, *, access_token: str, timeout_s: int = 30) -> None:
        self.access_token = str(access_token or "").strip()
        self.timeout_s = max(1, min(int(timeout_s), 120))

    def lookup(
        self,
        *,
        internet_message_id: str,
        recipient_email: str,
    ) -> MicrosoftGraphMessageTraceResult:
        message_id = str(internet_message_id or "").strip()
        recipient = str(recipient_email or "").strip().lower()
        if not self.access_token:
            return MicrosoftGraphMessageTraceResult(
                False, False, 0, 0,
                error_code="missing_microsoft_graph_message_trace_access_token",
            )
        if not message_id or len(message_id) > 1000 or "@" not in recipient:
            return MicrosoftGraphMessageTraceResult(
                False, False, 0, 0,
                error_code="microsoft_graph_message_trace_reference_invalid",
            )
        try:
            import requests
        except Exception as exc:
            return MicrosoftGraphMessageTraceResult(
                False, False, 0, 0, error_code=f"requests_import_failed:{exc}",
            )
        escaped_message = message_id.replace("'", "''")
        escaped_recipient = recipient.replace("'", "''")
        started = time.time()
        try:
            response = requests.get(
                self.ENDPOINT,
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={
                    "$filter": (
                        f"messageId eq '{escaped_message}' and "
                        f"recipientAddress eq '{escaped_recipient}'"
                    ),
                    "$top": "10",
                },
                timeout=self.timeout_s,
            )
            latency_ms = int((time.time() - started) * 1000)
            if response.status_code != 200:
                return MicrosoftGraphMessageTraceResult(
                    False, False, response.status_code, latency_ms,
                    error_code=f"microsoft_graph_message_trace_failed:{response.status_code}",
                )
            try:
                body = dict(response.json() or {})
            except Exception:
                body = {}
            candidates = []
            for raw in body.get("value") or []:
                if not isinstance(raw, dict):
                    continue
                if str(raw.get("messageId") or "") != message_id:
                    continue
                if str(raw.get("recipientAddress") or "").strip().lower() != recipient:
                    continue
                candidates.append(raw)
            if not candidates:
                return MicrosoftGraphMessageTraceResult(True, False, 200, latency_ms)
            candidates.sort(key=lambda item: str(item.get("receivedDateTime") or ""), reverse=True)
            match = candidates[0]
            return MicrosoftGraphMessageTraceResult(
                True, True, 200, latency_ms,
                trace_id=str(match.get("id") or "")[:500],
                internet_message_id=message_id,
                provider_status=str(match.get("status") or "").strip(),
                observed_at=str(match.get("receivedDateTime") or "")[:64]
                or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
        except Exception as exc:
            return MicrosoftGraphMessageTraceResult(
                False, False, 0, int((time.time() - started) * 1000),
                error_code=f"microsoft_graph_message_trace_request_failed:{exc}",
            )
