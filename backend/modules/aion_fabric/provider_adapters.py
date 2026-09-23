from __future__ import annotations

import base64
import hmac
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Callable, Dict

from .canonical import canonical_bytes, canonical_hash
from .google_oauth import PersonaGoogleOAuth


class GoogleAdapterBase:
    def __init__(self, token_resolver: Callable[[str], str], *, urlopen: Callable[..., Any] | None = None) -> None:
        self.token_resolver = token_resolver
        self.urlopen = urlopen or urllib.request.urlopen

    def _request(self, url: str, payload: Dict[str, Any] | None, credential_reference: str, *, method: str = "POST") -> Dict[str, Any]:
        if not credential_reference.startswith("provider://google/"):
            raise PermissionError("This adapter requires a Google provider binding")
        token = str(self.token_resolver(credential_reference) or "")
        if len(token) < 20 or any(character.isspace() for character in token):
            raise PermissionError("The Google provider binding is unavailable")
        request = urllib.request.Request(
            url,
            data=canonical_bytes(payload) if payload is not None else None,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"},
            method=method,
        )
        try:
            with self.urlopen(request, timeout=30) as response:
                body = response.read(512_001)
            if len(body) > 512_000:
                raise RuntimeError("Google adapter response exceeded its safety limit")
            value = json.loads(body) if body.strip() else {}
            if not isinstance(value, dict):
                raise RuntimeError("Google adapter returned an invalid response")
            return value
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Google adapter request failed with HTTP {exc.code}") from exc
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Google adapter could not verify the provider response") from exc

    def _post(self, url: str, payload: Dict[str, Any], credential_reference: str) -> Dict[str, Any]:
        return self._request(url, payload, credential_reference, method="POST")


class GoogleCalendarAdapter(GoogleAdapterBase):
    """Approved Google Calendar event creation with a deterministic event ID."""

    @staticmethod
    def _time(value: str) -> str:
        cleaned = str(value).strip()
        try:
            datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Calendar start/end must be ISO-8601 date-times") from exc
        return cleaned

    def __call__(self, proposal: Dict[str, Any], credential_reference: str) -> Dict[str, Any]:
        parameters = dict(proposal.get("scope") or proposal.get("parameters") or {})
        title = " ".join(str(parameters.get("title") or "").split()).strip()[:240]
        if not title:
            raise ValueError("Calendar event title is required")
        event_id = canonical_hash({"proposal_id": proposal["proposal_id"], "persona_id": proposal["persona_id"]})[:32]
        event: Dict[str, Any] = {
            "id": event_id,
            "summary": title,
            "start": {"dateTime": self._time(str(parameters.get("start") or "")), "timeZone": str(parameters.get("time_zone") or "Europe/Madrid")[:80]},
            "end": {"dateTime": self._time(str(parameters.get("end") or "")), "timeZone": str(parameters.get("time_zone") or "Europe/Madrid")[:80]},
        }
        for source, target, limit in (("description", "description", 1500), ("location", "location", 300)):
            value = " ".join(str(parameters.get(source) or "").split()).strip()
            if value:
                event[target] = value[:limit]
        attendees = []
        for address in list(parameters.get("attendees") or [])[:20]:
            address = str(address).strip().lower()
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", address):
                raise ValueError("Invalid calendar attendee address")
            attendees.append({"email": address})
        if attendees:
            event["attendees"] = attendees
        calendar_id = urllib.parse.quote(str(parameters.get("calendar_id") or "primary"), safe="")
        notify = "all" if parameters.get("notify_attendees") else "none"
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events?sendUpdates={notify}"
        response = self._post(url, event, credential_reference)
        if str(response.get("id") or "") != event_id or str(response.get("status") or "") not in {"confirmed", "tentative"}:
            raise RuntimeError("Google Calendar did not verify the created event")
        return {"verified": True, "external_reference": str(response.get("htmlLink") or response["id"]), "provider": "google_calendar", "event_id": response["id"], "provider_event_id": response["id"], "provider_status": str(response["status"])}


class GoogleCalendarModifyAdapter(GoogleAdapterBase):
    """Exact approved Google Calendar reschedule or cancellation."""

    def __init__(self, token_resolver: Callable[[str], str], *, action: str, urlopen: Callable[..., Any] | None = None) -> None:
        super().__init__(token_resolver, urlopen=urlopen)
        if action not in {"reschedule", "cancel"}:
            raise ValueError("Calendar modification action is invalid")
        self.action = action

    def __call__(self, proposal: Dict[str, Any], credential_reference: str) -> Dict[str, Any]:
        scope = dict(proposal.get("scope") or proposal.get("parameters") or {})
        event_id = str(scope.get("provider_event_id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{4,240}", event_id):
            raise ValueError("An exact Google Calendar event ID is required")
        calendar_id = urllib.parse.quote(str(scope.get("calendar_id") or "primary"), safe="")
        quoted_event = urllib.parse.quote(event_id, safe="")
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{quoted_event}"
        if self.action == "cancel":
            response = self._request(url, None, credential_reference, method="DELETE")
            if response not in ({}, {"status": "cancelled"}) and str(response.get("id") or event_id) != event_id:
                raise RuntimeError("Google Calendar did not verify the cancellation")
            return {"verified": True, "provider_event_id": event_id, "provider_status": "cancelled", "external_reference": event_id}
        payload = {
            "start": {"dateTime": GoogleCalendarAdapter._time(str(scope.get("start") or "")), "timeZone": str(scope.get("time_zone") or "Europe/Madrid")[:80]},
            "end": {"dateTime": GoogleCalendarAdapter._time(str(scope.get("end") or "")), "timeZone": str(scope.get("time_zone") or "Europe/Madrid")[:80]},
        }
        response = self._request(url, payload, credential_reference, method="PATCH")
        if str(response.get("id") or "") != event_id or str(response.get("status") or "") not in {"confirmed", "tentative"}:
            raise RuntimeError("Google Calendar did not verify the reschedule")
        return {"verified": True, "provider_event_id": event_id, "provider_status": str(response["status"]), "external_reference": str(response.get("htmlLink") or event_id)}


class GmailSendAdapter(GoogleAdapterBase):
    """Approved Gmail send using a deterministic Message-ID for reconciliation."""

    def __call__(self, proposal: Dict[str, Any], credential_reference: str) -> Dict[str, Any]:
        parameters = dict(proposal.get("parameters") or {})
        recipients = parameters.get("to")
        if isinstance(recipients, str):
            recipients = [recipients]
        recipients = [str(item).strip().lower() for item in list(recipients or [])[:20]]
        if not recipients or any(not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", item) for item in recipients):
            raise ValueError("At least one valid email recipient is required")
        subject = " ".join(str(parameters.get("subject") or "").split()).strip()[:240]
        body = str(parameters.get("body") or "")[:20_000]
        if not subject or not body.strip():
            raise ValueError("Email subject and body are required")
        message = EmailMessage()
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message["Message-ID"] = f"<{canonical_hash(proposal['proposal_id'])[:32]}@aion.local>"
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
        response = self._post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", {"raw": raw}, credential_reference)
        message_id = str(response.get("id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{4,200}", message_id):
            raise RuntimeError("Gmail did not verify the sent message")
        return {"verified": True, "external_reference": message_id, "provider": "gmail", "message_id": message_id, "thread_id": str(response.get("threadId") or "")[:200]}


class PersonaBoundGmailCommunicationAdapter:
    """Resolve Gmail authority for the exact sender without exposing OAuth to the phone."""

    def __init__(
        self,
        oauth: PersonaGoogleOAuth,
        access_token_resolver: Callable[[str], str],
        *,
        urlopen: Callable[..., Any] | None = None,
    ) -> None:
        self.oauth = oauth
        self.access_token_resolver = access_token_resolver
        self.urlopen = urlopen

    def __call__(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        persona_id = str(draft.get("persona_id") or "")
        binding = self.oauth.authorized_binding(persona_id=persona_id, service="email_send")
        vault_reference = str(binding["vault_reference"])
        provider_reference = f"provider://google/email/{binding['binding_id']}"
        adapter = GmailSendAdapter(
            lambda _reference: self.access_token_resolver(vault_reference),
            urlopen=self.urlopen,
        )
        result = adapter(
            {
                "proposal_id": str(draft.get("draft_id") or ""),
                "persona_id": persona_id,
                "parameters": {
                    "to": [str(draft.get("recipient") or "")],
                    "subject": str(draft.get("subject") or "(no subject)"),
                    "body": str(draft.get("body") or ""),
                },
            },
            provider_reference,
        )
        return {
            "verified": True,
            "provider_state": "provider_accepted",
            "provider_message_id": result["message_id"],
            "provider_thread_id": result.get("thread_id", ""),
        }


class TwilioMessageAdapter:
    """Official Twilio Messages API boundary for approved SMS or WhatsApp sends.

    Credentials are resolved only during the approved external action.  The
    adapter returns a narrow provider receipt and deliberately does not treat
    Twilio acceptance as handset delivery or human reading.
    """

    _E164 = re.compile(r"^\+[1-9][0-9]{6,14}$")
    _ACCOUNT = re.compile(r"^AC[a-fA-F0-9]{32}$")
    _MESSAGE = re.compile(r"^SM[a-fA-F0-9]{32}$")

    def __init__(
        self,
        credential_resolver: Callable[[str], Dict[str, str]],
        *,
        channel: str = "sms",
        urlopen: Callable[..., Any] | None = None,
    ) -> None:
        if channel not in {"sms", "whatsapp"}:
            raise ValueError("Twilio channel must be SMS or WhatsApp")
        self.credential_resolver = credential_resolver
        self.channel = channel
        self.urlopen = urlopen or urllib.request.urlopen

    @classmethod
    def _number(cls, value: Any) -> str:
        number = re.sub(r"[\s()-]", "", str(value or ""))
        if not cls._E164.fullmatch(number):
            raise ValueError("Twilio recipients and senders must use E.164 format")
        return number

    def __call__(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        persona_id = str(draft.get("persona_id") or "")
        credentials = dict(self.credential_resolver(persona_id) or {})
        account = str(credentials.get("account_sid") or "")
        username = str(credentials.get("api_username") or account)
        secret = str(credentials.get("api_secret") or "")
        sender = self._number(credentials.get("from_number"))
        if not self._ACCOUNT.fullmatch(account) or len(username) < 10 or len(secret) < 16:
            raise PermissionError("A valid persona-bound Twilio account is required")
        recipient = self._number(draft.get("recipient"))
        body = str(draft.get("body") or "").strip()
        if not body or len(body) > 1600:
            raise ValueError("SMS and WhatsApp content must contain 1 to 1600 characters")
        prefix = "whatsapp:" if self.channel == "whatsapp" else ""
        parameters = {"To": prefix + recipient, "From": prefix + sender, "Body": body}
        callback = str(credentials.get("status_callback") or "").strip()
        if callback:
            parsed = urllib.parse.urlparse(callback)
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("Twilio status callbacks require a public HTTPS URL")
            parameters["StatusCallback"] = callback
        encoded = urllib.parse.urlencode(parameters).encode("utf-8")
        token = base64.b64encode(f"{username}:{secret}".encode("utf-8")).decode("ascii")
        request = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{urllib.parse.quote(account, safe='')}/Messages.json",
            data=encoded,
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Idempotency-Key": str(draft.get("draft_id") or "")[:200],
            },
            method="POST",
        )
        try:
            with self.urlopen(request, timeout=20) as response:
                raw = response.read(64_001)
            if len(raw) > 64_000:
                raise RuntimeError("Twilio response exceeded the safety limit")
            result = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Twilio message request failed with HTTP {exc.code}") from exc
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Twilio message acceptance could not be verified") from exc
        sid = str(result.get("sid") or "")
        status = str(result.get("status") or "")
        if not self._MESSAGE.fullmatch(sid) or status not in {
            "accepted", "queued", "sending", "sent", "delivered", "undelivered", "failed",
        }:
            raise RuntimeError("Twilio did not return a verifiable message receipt")
        return {
            "verified": True,
            "provider_state": "provider_accepted",
            "provider_message_id": sid,
            "provider_thread_id": "",
            "provider": f"twilio_{self.channel}",
            "provider_status": status,
            "human_delivery_verified": False,
            "provider_response_retained": False,
        }

    @staticmethod
    def verify_status_callback(*, url: str, parameters: Dict[str, Any], signature: str, auth_token: str) -> bool:
        """Verify Twilio's HMAC-SHA1 webhook signature using the exact public URL."""
        if not url.startswith("https://") or not signature or len(auth_token) < 16:
            return False
        material = url + "".join(str(key) + str(parameters[key]) for key in sorted(parameters))
        digest = hmac.new(auth_token.encode("utf-8"), material.encode("utf-8"), hashlib.sha1).digest()
        expected = base64.b64encode(digest).decode("ascii")
        return hmac.compare_digest(expected, signature)


class GoogleTasksAdapter(GoogleAdapterBase):
    """Create one approved task through the official Google Tasks v1 endpoint."""

    def __call__(self, task: Dict[str, Any], credential_reference: str) -> Dict[str, Any]:
        title = " ".join(str(task.get("title") or "").split())[:1024]
        if not title:
            raise ValueError("Google task title is required")
        payload: Dict[str, Any] = {"title": title}
        notes = str(task.get("notes") or "")[:8192]
        if notes:
            payload["notes"] = notes
        due = str(task.get("snoozed_until") or "")
        if due:
            try:
                datetime.fromisoformat(due.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("Google task due time must be ISO-8601") from exc
            payload["due"] = due
        tasklist = urllib.parse.quote(str(task.get("provider_tasklist") or "@default"), safe="")
        response = self._post(f"https://tasks.googleapis.com/tasks/v1/lists/{tasklist}/tasks", payload, credential_reference)
        task_id = str(response.get("id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{4,240}", task_id) or str(response.get("title") or "") != title:
            raise RuntimeError("Google Tasks did not verify the created task")
        return {
            "verified": True,
            "external_reference": str(response.get("selfLink") or task_id)[:1000],
            "provider": "google_tasks",
            "provider_task_id": task_id,
            "provider_status": str(response.get("status") or "needsAction")[:80],
        }
