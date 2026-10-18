from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json

import pytest

from backend.modules.aion_business.runtime.legal_delivery_service import (
    LegalDeliveryError,
    LegalDeliveryService,
)


def _queue(service: LegalDeliveryService, workspace: str = "w") -> dict:
    return service.queue(
        workspace,
        envelope_id="envelope-1",
        manifest_hash="ab" * 32,
        signer={"signer_id": "signer-1", "email": "party@example.com"},
        provider="resend",
        subject="Completed agreement",
        body_text="Private delivery message",
        attachment_name="agreement.tessaris-evidence.zip",
        attachment_bytes=b"exact-private-evidence-package",
        approved_by="owner",
        acknowledge_external_send=True,
    )


def _queue_microsoft(service: LegalDeliveryService, workspace: str = "w") -> dict:
    return service.queue(
        workspace,
        envelope_id="envelope-ms-1",
        manifest_hash="cd" * 32,
        signer={"signer_id": "signer-ms-1", "email": "party@example.com"},
        provider="microsoft_graph",
        subject="Completed agreement",
        body_text="Private delivery message",
        attachment_name="agreement.tessaris-evidence.zip",
        attachment_bytes=b"exact-private-evidence-package",
        approved_by="owner",
        acknowledge_external_send=True,
    )


def _resend_headers(raw: bytes, *, event_id: str, timestamp: int, secret: str) -> dict[str, str]:
    encoded = secret.removeprefix("whsec_")
    key = base64.urlsafe_b64decode(encoded + ("=" * (-len(encoded) % 4)))
    signed = f"{event_id}.{timestamp}.".encode("utf-8") + raw
    signature = base64.b64encode(hmac.new(key, signed, sha256).digest()).decode("ascii")
    return {
        "svix-id": event_id,
        "svix-timestamp": str(timestamp),
        "svix-signature": f"v1,{signature}",
    }


def test_delivery_outbox_is_encrypted_redacted_and_idempotent(tmp_path):
    service = LegalDeliveryService(tmp_path)
    first = _queue(service)
    second = _queue(service)

    assert first["delivery_id"] == second["delivery_id"]
    assert first["message"]["body_text"] == "Signed evidence package prepared for approved delivery."
    assert "content_base64" not in first["attachment"]
    path = next((tmp_path / "_delivery_outbox" / "w").glob("*.enc"))
    encrypted = path.read_text(encoding="utf-8")
    assert "party@example.com" not in encrypted
    assert "Private delivery message" not in encrypted
    assert "exact-private-evidence-package" not in encrypted

    stored = service._load("w", first["delivery_id"])
    assert base64.b64decode(stored["attachment"]["content_base64"]) == b"exact-private-evidence-package"
    assert service.status("w", "envelope-1")["event_chains_valid"] is True
    assert len(service.status("w", "envelope-1")["items"]) == 1


def test_delivery_requires_explicit_external_send_acknowledgement(tmp_path):
    service = LegalDeliveryService(tmp_path)
    with pytest.raises(LegalDeliveryError, match="external_send_acknowledgement_required"):
        service.queue(
            "w", envelope_id="envelope-1", manifest_hash="ab" * 32,
            signer={"signer_id": "signer-1", "email": "party@example.com"},
            provider="resend", subject="Agreement", body_text="Body",
            attachment_name="evidence.zip", attachment_bytes=b"evidence",
            approved_by="owner", acknowledge_external_send=False,
        )
    with pytest.raises(LegalDeliveryError, match="external_send_acknowledgement_required"):
        service.deliver_due("w", actor_id="owner", acknowledge_external_send=False)


def test_provider_submission_is_not_delivery_until_confirmed(tmp_path):
    captured = {}

    def sender(record):
        captured.update(record)
        return {"ok": True, "provider_request_id": "provider-123", "provider_status": "accepted"}

    service = LegalDeliveryService(tmp_path, senders={"resend": sender})
    queued = _queue(service)
    sent = service.deliver_due("w", actor_id="owner", acknowledge_external_send=True)

    assert sent["attempted_count"] == 1
    assert sent["counts"] == {"SUBMITTED_TO_PROVIDER": 1}
    assert sent["all_required_parties_confirmed"] is False
    assert captured["message"]["body_text"] == "Private delivery message"
    assert base64.b64decode(captured["attachment"]["content_base64"]) == b"exact-private-evidence-package"

    confirmed = service.confirm(
        "w", queued["delivery_id"], outcome="DELIVERED",
        provider_reference="provider-delivery-event-456", actor_id="system",
    )
    assert confirmed["status"] == "DELIVERED"
    assert service.status("w", "envelope-1")["all_required_parties_confirmed"] is True
    with pytest.raises(LegalDeliveryError, match="delivery_confirmation_conflict"):
        service.confirm(
            "w", queued["delivery_id"], outcome="BOUNCED",
            provider_reference="different-event", actor_id="system",
        )


def test_bounced_delivery_can_be_explicitly_reauthorized_and_retried(tmp_path):
    service = LegalDeliveryService(
        tmp_path,
        senders={"resend": lambda _record: {
            "ok": True, "provider_request_id": "request-1", "provider_status": "accepted",
        }},
    )
    queued = _queue(service)
    service.deliver_due("w", actor_id="owner", acknowledge_external_send=True)
    service.confirm(
        "w", queued["delivery_id"], outcome="BOUNCED",
        provider_reference="bounce-event-1", actor_id="provider_webhook",
    )
    with pytest.raises(LegalDeliveryError, match="external_send_acknowledgement_required"):
        service.retry_or_resend(
            "w", queued["delivery_id"], actor_id="owner", reason="Corrected recipient",
            acknowledge_external_send=False,
        )
    retry = service.retry_or_resend(
        "w", queued["delivery_id"], actor_id="owner", reason="Recipient mailbox restored",
        acknowledge_external_send=True,
    )
    assert retry["status"] == "RETRY_PENDING"
    assert retry["provider_history"][0]["status"] == "BOUNCED"
    assert retry["provider_history"][0]["confirmation_reference"] == "bounce-event-1"
    resent = service.deliver_due(
        "w", actor_id="owner", acknowledge_external_send=True, force=True,
    )
    assert resent["counts"] == {"SUBMITTED_TO_PROVIDER": 1}
    assert resent["items"][0]["attempt_count"] == 2


def test_retry_survives_restart_and_workspace_isolation(tmp_path):
    now = [datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)]

    def unavailable(_record):
        raise RuntimeError("provider temporarily unavailable")

    first = LegalDeliveryService(tmp_path, clock=lambda: now[0], senders={"resend": unavailable})
    queued = _queue(first)
    failed = first.deliver_due("w", actor_id="owner", acknowledge_external_send=True)
    assert failed["counts"] == {"RETRY_PENDING": 1}
    assert failed["items"][0]["attempt_count"] == 1
    assert failed["items"][0]["next_attempt_at"] == "2026-09-26T12:00:30Z"
    assert first.status("other", "envelope-1")["items"] == []
    with pytest.raises(LegalDeliveryError, match="legal_delivery_not_found"):
        first.confirm(
            "other", queued["delivery_id"], outcome="DELIVERED",
            provider_reference="wrong-workspace", actor_id="owner",
        )

    now[0] += timedelta(seconds=31)
    restarted = LegalDeliveryService(
        tmp_path, clock=lambda: now[0],
        senders={"resend": lambda _record: {
            "ok": True, "provider_request_id": "retry-accepted", "provider_status": "accepted",
        }},
    )
    recovered = restarted.deliver_due("w", actor_id="owner", acknowledge_external_send=True)
    assert recovered["counts"] == {"SUBMITTED_TO_PROVIDER": 1}
    assert recovered["items"][0]["attempt_count"] == 2
    assert recovered["event_chains_valid"] is True


def test_tampered_delivery_event_chain_is_rejected(tmp_path):
    service = LegalDeliveryService(tmp_path)
    queued = _queue(service)
    path = next((tmp_path / "_delivery_outbox" / "w").glob("*.enc"))
    record = service._load("w", queued["delivery_id"])
    record["events"][0]["actor_id"] = "tampered"
    service.store.write(path, record, workspace_id="w", record_id=queued["delivery_id"])
    with pytest.raises(LegalDeliveryError, match="legal_delivery_event_chain_invalid"):
        service.status("w")


def test_resend_webhook_is_authenticated_idempotent_and_updates_delivery(tmp_path):
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    secret = "whsec_" + base64.urlsafe_b64encode(b"w" * 32).decode("ascii")
    service = LegalDeliveryService(
        tmp_path,
        clock=lambda: now,
        senders={"resend": lambda _record: {
            "ok": True, "provider_request_id": "email-provider-1", "provider_status": "accepted",
        }},
    )
    _queue(service)
    service.deliver_due("w", actor_id="owner", acknowledge_external_send=True)

    delayed_raw = json.dumps({
        "type": "email.delivery_delayed", "created_at": "2026-09-26T12:00:00Z",
        "data": {"email_id": "email-provider-1", "to": ["party@example.com"]},
    }, separators=(",", ":")).encode("utf-8")
    delayed_headers = _resend_headers(
        delayed_raw, event_id="msg-delayed-1", timestamp=int(now.timestamp()), secret=secret,
    )
    delayed = service.ingest_resend_webhook(
        delayed_raw, delayed_headers, webhook_secrets=secret,
    )
    assert delayed["outcome"] == "DELIVERY_DELAYED"
    assert service.status("w")["counts"] == {"DELIVERY_DELAYED": 1}

    duplicate = service.ingest_resend_webhook(
        delayed_raw, delayed_headers, webhook_secrets=secret,
    )
    assert duplicate["duplicate"] is True
    assert len(service._records("w")[0]["provider_events"]) == 1

    delivered_raw = json.dumps({
        "type": "email.delivered", "created_at": "2026-09-26T12:00:01Z",
        "data": {"email_id": "email-provider-1", "to": ["party@example.com"]},
    }, separators=(",", ":")).encode("utf-8")
    delivered = service.ingest_resend_webhook(
        delivered_raw,
        _resend_headers(delivered_raw, event_id="msg-delivered-1", timestamp=int(now.timestamp()), secret=secret),
        webhook_secrets=[secret],
    )
    assert delivered["outcome"] == "DELIVERED"
    status = service.status("w", "envelope-1")
    assert status["all_required_parties_confirmed"] is True
    assert status["event_chains_valid"] is True


def test_resend_webhook_rejects_tampering_stale_events_and_event_id_conflicts(tmp_path):
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    secret = "whsec_" + base64.urlsafe_b64encode(b"s" * 32).decode("ascii")
    service = LegalDeliveryService(tmp_path, clock=lambda: now)
    raw = b'{"type":"email.delivered","data":{"email_id":"unknown"}}'
    headers = _resend_headers(raw, event_id="msg-1", timestamp=int(now.timestamp()), secret=secret)

    with pytest.raises(LegalDeliveryError, match="resend_webhook_signature_invalid"):
        service.ingest_resend_webhook(raw + b" ", headers, webhook_secrets=secret)
    stale = _resend_headers(raw, event_id="msg-stale", timestamp=int(now.timestamp()) - 301, secret=secret)
    with pytest.raises(LegalDeliveryError, match="resend_webhook_timestamp_outside_tolerance"):
        service.ingest_resend_webhook(raw, stale, webhook_secrets=secret)


def test_resend_webhook_duplicate_is_durable_across_service_restart(tmp_path):
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    secret = "whsec_" + base64.urlsafe_b64encode(b"r" * 32).decode("ascii")
    service = LegalDeliveryService(
        tmp_path,
        clock=lambda: now,
        senders={"resend": lambda _record: {
            "ok": True,
            "provider_request_id": "email-provider-restart",
            "provider_status": "accepted",
        }},
    )
    _queue(service)
    service.deliver_due("w", actor_id="owner", acknowledge_external_send=True)
    raw = json.dumps({
        "type": "email.delivered",
        "data": {"email_id": "email-provider-restart"},
    }, separators=(",", ":")).encode("utf-8")
    headers = _resend_headers(
        raw,
        event_id="msg-restart-1",
        timestamp=int(now.timestamp()),
        secret=secret,
    )
    first = service.ingest_resend_webhook(raw, headers, webhook_secrets=secret)
    assert first["duplicate"] is False

    restarted = LegalDeliveryService(tmp_path, clock=lambda: now)
    duplicate = restarted.ingest_resend_webhook(raw, headers, webhook_secrets=secret)
    assert duplicate["duplicate"] is True

    conflicting_raw = json.dumps({
        "type": "email.bounced",
        "data": {"email_id": "email-provider-restart"},
    }, separators=(",", ":")).encode("utf-8")
    conflicting_headers = _resend_headers(
        conflicting_raw,
        event_id="msg-restart-1",
        timestamp=int(now.timestamp()),
        secret=secret,
    )
    with pytest.raises(LegalDeliveryError, match="resend_webhook_event_id_conflict"):
        restarted.ingest_resend_webhook(
            conflicting_raw,
            conflicting_headers,
            webhook_secrets=secret,
        )


def test_resend_conflicting_final_outcome_is_retained_for_human_review(tmp_path):
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    secret = "whsec_" + base64.urlsafe_b64encode(b"c" * 32).decode("ascii")
    service = LegalDeliveryService(
        tmp_path, clock=lambda: now,
        senders={"resend": lambda _record: {
            "ok": True, "provider_request_id": "email-provider-conflict", "provider_status": "accepted",
        }},
    )
    _queue(service)
    service.deliver_due("w", actor_id="owner", acknowledge_external_send=True)

    for event_id, event_type in (("msg-delivered", "email.delivered"), ("msg-bounced", "email.bounced")):
        raw = json.dumps({
            "type": event_type, "data": {"email_id": "email-provider-conflict"},
        }, separators=(",", ":")).encode("utf-8")
        result = service.ingest_resend_webhook(
            raw,
            _resend_headers(raw, event_id=event_id, timestamp=int(now.timestamp()), secret=secret),
            webhook_secrets=secret,
        )

    assert result["conflict"] is True
    stored = service._records("w")[0]
    assert stored["status"] == "DELIVERED"
    assert stored["provider_outcome_conflict"]["conflicting_status"] == "BOUNCED"
    assert stored["provider_outcome_conflict"]["requires_human_review"] is True


def test_microsoft_message_trace_is_idempotent_and_is_the_delivery_authority(tmp_path):
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)

    def checker(record):
        return {
            "ok": True,
            "found": True,
            "trace_id": "exchange-trace-1",
            "internet_message_id": record["provider_request_id"],
            "provider_status": "delivered",
            "observed_at": "2026-09-26T12:00:10Z",
        }

    service = LegalDeliveryService(
        tmp_path,
        clock=lambda: now,
        senders={"microsoft_graph": lambda _record: {
            "ok": True,
            "provider_request_id": "<message-1@example.onmicrosoft.com>",
            "provider_status": "submitted",
        }},
        receipt_checkers={"microsoft_graph": checker},
    )
    _queue_microsoft(service)
    submitted = service.deliver_due("w", actor_id="owner", acknowledge_external_send=True)
    assert submitted["counts"] == {"SUBMITTED_TO_PROVIDER": 1}
    assert submitted["all_required_parties_confirmed"] is False

    refreshed = service.refresh_provider_receipts(
        "w", provider="microsoft_graph", actor_id="message_trace", limit=10,
    )
    assert refreshed["counts"] == {"DELIVERED": 1}
    assert refreshed["updated_count"] == 1
    assert refreshed["all_required_parties_confirmed"] is True
    assert refreshed["items"][0]["confirmation_reference"] == "exchange-trace-1"

    duplicate = service.refresh_provider_receipts(
        "w", provider="microsoft_graph", actor_id="message_trace", limit=10,
    )
    assert duplicate["updated_count"] == 0
    assert len(service._records("w")[0]["provider_events"]) == 1


def test_microsoft_quarantine_is_delayed_and_requires_human_review(tmp_path):
    service = LegalDeliveryService(
        tmp_path,
        senders={"microsoft_graph": lambda _record: {
            "ok": True,
            "provider_request_id": "<message-2@example.onmicrosoft.com>",
            "provider_status": "submitted",
        }},
        receipt_checkers={"microsoft_graph": lambda record: {
            "ok": True,
            "found": True,
            "trace_id": "exchange-trace-quarantine",
            "internet_message_id": record["provider_request_id"],
            "provider_status": "quarantined",
            "observed_at": "2026-09-26T12:00:10Z",
        }},
    )
    _queue_microsoft(service)
    service.deliver_due("w", actor_id="owner", acknowledge_external_send=True)
    refreshed = service.refresh_provider_receipts(
        "w", provider="microsoft_graph", actor_id="message_trace",
    )
    item = refreshed["items"][0]
    assert item["status"] == "DELIVERY_DELAYED"
    assert item["requires_human_review"] is True
    assert refreshed["all_required_parties_confirmed"] is False
