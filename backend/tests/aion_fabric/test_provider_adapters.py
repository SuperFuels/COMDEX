from __future__ import annotations

import json

import pytest

from backend.modules.aion_fabric.google_oauth import PersonaGoogleOAuth
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.aion_fabric.provider_adapters import GmailSendAdapter, GoogleCalendarAdapter, GoogleCalendarModifyAdapter, PersonaBoundGmailCommunicationAdapter, TwilioMessageAdapter


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, limit):
        return self.payload


class EmptyResponse(FakeResponse):
    def __init__(self):
        self.payload = b""


def test_google_calendar_adapter_uses_persona_binding_and_verifies_event():
    seen = {}
    proposal = {
        "proposal_id": "service_proposal_calendar",
        "persona_id": "persona_one",
        "parameters": {
            "title": "Granada trip",
            "start": "2026-09-12T09:00:00+02:00",
            "end": "2026-09-12T10:00:00+02:00",
            "time_zone": "Europe/Madrid",
        },
    }

    def opener(request, timeout):
        payload = json.loads(request.data)
        seen.update({"url": request.full_url, "payload": payload, "authorization": request.headers["Authorization"]})
        return FakeResponse({"id": payload["id"], "status": "confirmed", "htmlLink": "https://calendar.google.com/event/verified"})

    adapter = GoogleCalendarAdapter(lambda reference: "x" * 40, urlopen=opener)
    result = adapter(proposal, "provider://google/calendar/account-one")
    assert result["verified"] is True
    assert "/calendars/primary/events" in seen["url"]
    assert seen["payload"]["summary"] == "Granada trip"
    assert seen["authorization"] == "Bearer " + "x" * 40


def test_gmail_adapter_builds_message_and_requires_verified_provider_id():
    seen = {}

    def opener(request, timeout):
        seen.update({"url": request.full_url, "payload": json.loads(request.data)})
        return FakeResponse({"id": "gmail_message_123", "threadId": "thread_123"})

    adapter = GmailSendAdapter(lambda reference: "y" * 40, urlopen=opener)
    result = adapter(
        {
            "proposal_id": "service_proposal_email",
            "persona_id": "persona_one",
            "parameters": {"to": ["person@example.com"], "subject": "Trip options", "body": "Here is the approved shortlist."},
        },
        "provider://google/gmail/account-one",
    )
    assert result["verified"] is True
    assert seen["url"] == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    assert seen["payload"]["raw"]


def test_persona_bound_gmail_requires_exact_oauth_owner_and_keeps_vault_reference_private(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    owner = identities.onboard(display_name="Owner")
    other = identities.onboard(display_name="Other")
    oauth = PersonaGoogleOAuth(tmp_path, identities=identities)
    started = oauth.begin(
        persona_id=owner["persona_id"], services=["email_send"],
        client_id="pilot.apps.googleusercontent.com",
        redirect_uri="http://127.0.0.1:49152/oauth/callback",
    )
    oauth.complete(
        authorization_id=started["authorization_id"], state_token=started["state"], code="code",
        token_exchange=lambda pending, _code: {
            "access_token": "access", "refresh_token": "refresh", "expires_in": 3600,
            "token_type": "Bearer", "scope": " ".join(pending["scopes"]),
        },
        vault_store=lambda *_: "vault://platform/owner-google",
    )
    seen = {}

    def opener(request, timeout):
        seen["authorization"] = request.headers["Authorization"]
        return FakeResponse({"id": "gmail_persona_msg", "threadId": "gmail_thread"})

    adapter = PersonaBoundGmailCommunicationAdapter(
        oauth,
        lambda reference: "t" * 40 if reference == "vault://platform/owner-google" else "",
        urlopen=opener,
    )
    result = adapter({
        "draft_id": "draft_one", "persona_id": owner["persona_id"],
        "recipient": "person@example.com", "subject": "Hello", "body": "Exact approved body",
    })
    assert result["provider_state"] == "provider_accepted"
    assert seen["authorization"] == "Bearer " + "t" * 40
    with pytest.raises(PermissionError):
        adapter({
            "draft_id": "draft_two", "persona_id": other["persona_id"],
            "recipient": "person@example.com", "subject": "Hello", "body": "Not authorized",
        })


def test_google_calendar_reschedule_and_cancel_are_exact_verified_actions():
    seen = []
    def opener(request, timeout):
        seen.append((request.get_method(), request.full_url))
        if request.get_method() == "DELETE":
            return EmptyResponse()
        return FakeResponse({"id": "event_123", "status": "confirmed", "htmlLink": "https://calendar.google.com/event/123"})
    proposal = {"scope": {"provider_event_id": "event_123", "start": "2026-09-12T11:00:00+02:00", "end": "2026-09-12T12:00:00+02:00"}}
    rescheduled = GoogleCalendarModifyAdapter(lambda _reference: "z" * 40, action="reschedule", urlopen=opener)(proposal, "provider://google/calendar/account-one")
    cancelled = GoogleCalendarModifyAdapter(lambda _reference: "z" * 40, action="cancel", urlopen=opener)(proposal, "provider://google/calendar/account-one")
    assert rescheduled["verified"] is True and cancelled["provider_status"] == "cancelled"
    assert seen[0][0] == "PATCH" and seen[1][0] == "DELETE"


def test_twilio_sms_adapter_uses_persona_credentials_and_returns_narrow_acceptance():
    seen = {}

    def opener(request, timeout):
        seen.update({
            "url": request.full_url,
            "body": request.data.decode(),
            "authorization": request.headers["Authorization"],
            "idempotency": request.headers["Idempotency-key"],
        })
        return FakeResponse({"sid": "SM" + "1" * 32, "status": "queued", "body": "must not be retained"})

    adapter = TwilioMessageAdapter(
        lambda persona_id: {
            "account_sid": "AC" + "2" * 32,
            "api_username": "SK" + "3" * 32,
            "api_secret": "secret-value-that-remains-in-vault",
            "from_number": "+34600000111",
            "status_callback": "https://pilot.example/provider/twilio/status",
        } if persona_id == "persona_one" else {},
        urlopen=opener,
    )
    result = adapter({
        "draft_id": "draft_sms_1", "persona_id": "persona_one",
        "recipient": "+34600000222", "body": "Exact approved text",
    })
    assert result == {
        "verified": True, "provider_state": "provider_accepted",
        "provider_message_id": "SM" + "1" * 32, "provider_thread_id": "",
        "provider": "twilio_sms", "provider_status": "queued",
        "human_delivery_verified": False, "provider_response_retained": False,
    }
    assert seen["url"].endswith("/Messages.json")
    assert "To=%2B34600000222" in seen["body"]
    assert "StatusCallback=https%3A%2F%2Fpilot.example" in seen["body"]
    assert seen["authorization"].startswith("Basic ")
    assert seen["idempotency"] == "draft_sms_1"
    assert "must not be retained" not in str(result)


def test_twilio_whatsapp_adapter_and_callback_signature_are_bounded():
    def opener(request, timeout):
        assert "To=whatsapp%3A%2B34600000222" in request.data.decode()
        assert "From=whatsapp%3A%2B34600000111" in request.data.decode()
        return FakeResponse({"sid": "SM" + "a" * 32, "status": "accepted"})

    credentials = {
        "account_sid": "AC" + "b" * 32, "api_username": "SK" + "c" * 32,
        "api_secret": "another-private-provider-secret", "from_number": "+34600000111",
    }
    adapter = TwilioMessageAdapter(lambda _persona: credentials, channel="whatsapp", urlopen=opener)
    result = adapter({"draft_id": "draft_wa_1", "persona_id": "persona_one", "recipient": "+34600000222", "body": "Hello"})
    assert result["provider"] == "twilio_whatsapp"
    url = "https://pilot.example/provider/twilio/status"
    parameters = {"MessageSid": "SM" + "a" * 32, "MessageStatus": "delivered"}
    import base64, hashlib, hmac
    material = url + "".join(key + parameters[key] for key in sorted(parameters))
    signature = base64.b64encode(hmac.new(b"provider-auth-token", material.encode(), hashlib.sha1).digest()).decode()
    assert adapter.verify_status_callback(url=url, parameters=parameters, signature=signature, auth_token="provider-auth-token") is True
    assert adapter.verify_status_callback(url=url, parameters=parameters, signature="tampered", auth_token="provider-auth-token") is False
