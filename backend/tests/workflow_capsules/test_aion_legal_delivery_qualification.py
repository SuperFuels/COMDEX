from __future__ import annotations

import base64
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json

import pytest

from backend.modules.aion_business.runtime.legal_delivery_qualification import (
    LegalDeliveryQualificationError,
    LegalDeliveryQualificationEvaluator,
)
from backend.modules.aion_business.runtime.legal_delivery_service import LegalDeliveryService


NOW = datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc)
WEBHOOK_SECRET = "whsec_" + base64.urlsafe_b64encode(b"q" * 32).decode("ascii")


def _headers(raw: bytes, event_id: str) -> dict[str, str]:
    encoded = WEBHOOK_SECRET.removeprefix("whsec_")
    key = base64.urlsafe_b64decode(encoded + ("=" * (-len(encoded) % 4)))
    timestamp = str(int(NOW.timestamp()))
    signed = f"{event_id}.{timestamp}.".encode("utf-8") + raw
    signature = base64.b64encode(hmac.new(key, signed, sha256).digest()).decode("ascii")
    return {
        "svix-id": event_id,
        "svix-timestamp": timestamp,
        "svix-signature": f"v1,{signature}",
    }


def _configuration() -> dict:
    return {
        "resend": {
            "callback_url": "https://tessaris.example/legal/delivery/resend/webhook",
            "vault_connected": True,
            "signing_secret_registered": True,
        },
        "microsoft_graph": {
            "vault_connected": True,
            "granted_scopes": [
                "Mail.ReadWrite", "Mail.Send", "ExchangeMessageTrace.Read.All",
            ],
            "message_trace_service_principal_provisioned": True,
        },
    }


def _queue(service: LegalDeliveryService, provider: str, name: str) -> dict:
    return service.queue(
        "workspace-one",
        envelope_id=f"envelope-{name}",
        manifest_hash=sha256(name.encode()).hexdigest(),
        signer={"signer_id": f"signer-{name}", "email": f"{name}@example.com"},
        provider=provider,
        subject=f"Private {name} agreement",
        body_text=f"Private {name} message",
        attachment_name=f"{name}.zip",
        attachment_bytes=f"private-{name}-evidence".encode(),
        approved_by="owner",
        acknowledge_external_send=True,
    )


def _resend_event(
    service: LegalDeliveryService, delivery: dict, event_type: str, suffix: str,
) -> None:
    current = service._load("workspace-one", delivery["delivery_id"])
    raw = json.dumps({
        "type": event_type,
        "created_at": "2026-09-27T08:00:00Z",
        "data": {
            "email_id": current["provider_request_id"],
            "to": [current["recipient"]],
            "subject": current["message"]["subject"],
        },
    }, separators=(",", ":")).encode()
    service.ingest_resend_webhook(
        raw, _headers(raw, f"event-{suffix}"), webhook_secrets=WEBHOOK_SECRET,
    )


def _microsoft_trace(
    service: LegalDeliveryService, delivery: dict, status: str, suffix: str,
) -> None:
    current = service._load("workspace-one", delivery["delivery_id"])
    service._apply_provider_receipt(
        "workspace-one", delivery["delivery_id"],
        provider="microsoft_graph", actor_id="message_trace",
        result={
            "provider_status": status,
            "trace_id": f"trace-{suffix}",
            "observed_at": "2026-09-27T08:00:10Z",
            "internet_message_id": current["provider_request_id"],
        },
    )


def _qualified_service(tmp_path) -> LegalDeliveryService:
    def sender(record):
        attempt = int(record.get("attempt_count") or 0) + 1
        if record["provider"] == "microsoft_graph":
            request_id = f"<{record['envelope_id']}-{attempt}@example.onmicrosoft.com>"
        else:
            request_id = f"resend-{record['envelope_id']}-{attempt}"
        return {"ok": True, "provider_request_id": request_id, "provider_status": "accepted"}

    service = LegalDeliveryService(tmp_path, clock=lambda: NOW, senders={
        "resend": sender, "microsoft_graph": sender,
    })

    direct = _queue(service, "resend", "resend-direct")
    service.deliver_due("workspace-one", actor_id="owner", acknowledge_external_send=True)
    _resend_event(service, direct, "email.delivered", "resend-direct-delivered")

    for case, failure_event in (
        ("delayed", "email.delivery_delayed"),
        ("bounced", "email.bounced"),
        ("rejected", "email.failed"),
    ):
        delivery = _queue(service, "resend", f"resend-{case}")
        service.deliver_due("workspace-one", actor_id="owner", acknowledge_external_send=True)
        _resend_event(service, delivery, failure_event, f"resend-{case}-failure")
        service.retry_or_resend(
            "workspace-one", delivery["delivery_id"], actor_id="owner",
            reason=f"Authorised {case} recovery", acknowledge_external_send=True,
        )
        service.deliver_due(
            "workspace-one", actor_id="owner", acknowledge_external_send=True, force=True,
        )
        _resend_event(service, delivery, "email.delivered", f"resend-{case}-delivered")

    direct = _queue(service, "microsoft_graph", "microsoft-direct")
    service.deliver_due("workspace-one", actor_id="owner", acknowledge_external_send=True)
    _microsoft_trace(service, direct, "delivered", "microsoft-direct-delivered")

    for case, trace_status in (("delayed", "quarantined"), ("failed", "failed")):
        delivery = _queue(service, "microsoft_graph", f"microsoft-{case}")
        service.deliver_due("workspace-one", actor_id="owner", acknowledge_external_send=True)
        _microsoft_trace(service, delivery, trace_status, f"microsoft-{case}-failure")
        service.retry_or_resend(
            "workspace-one", delivery["delivery_id"], actor_id="owner",
            reason=f"Authorised {case} recovery", acknowledge_external_send=True,
        )
        service.deliver_due(
            "workspace-one", actor_id="owner", acknowledge_external_send=True, force=True,
        )
        _microsoft_trace(service, delivery, "delivered", f"microsoft-{case}-delivered")
    return service


def test_production_report_requires_all_authenticated_provider_paths(tmp_path):
    evaluator = LegalDeliveryQualificationEvaluator(_qualified_service(tmp_path))
    report = evaluator.evaluate(
        "workspace-one", environment="production",
        provider_configuration=_configuration(), generated_at="2026-09-27T09:00:00Z",
    )

    assert report["production_ready"] is True
    assert report["result"] == "PRODUCTION_PROVIDER_CASES_PASSED"
    assert report["integrity"]["evaluated_record_count"] == 7
    assert report["integrity"]["manual_only_delivery_count"] == 0
    assert all(item["passed"] for item in report["coverage"].values())
    assert evaluator.verify_report(report) is True

    rendered = json.dumps(report, sort_keys=True)
    assert "@example.com" not in rendered
    assert "Private" not in rendered
    assert "trace-" not in rendered
    assert "resend-envelope" not in rendered


def test_provider_acceptance_and_manual_confirmation_do_not_qualify(tmp_path):
    service = LegalDeliveryService(
        tmp_path,
        senders={"resend": lambda record: {
            "ok": True,
            "provider_request_id": f"accepted-{record['envelope_id']}",
            "provider_status": "accepted",
        }},
    )
    accepted = _queue(service, "resend", "accepted-only")
    service.deliver_due("workspace-one", actor_id="owner", acknowledge_external_send=True)
    manual = _queue(service, "resend", "manual-only")
    service.deliver_due("workspace-one", actor_id="owner", acknowledge_external_send=True)
    service.confirm(
        "workspace-one", manual["delivery_id"], outcome="DELIVERED",
        provider_reference="operator-assertion", actor_id="owner",
    )

    report = LegalDeliveryQualificationEvaluator(service).evaluate(
        "workspace-one", environment="production", provider_configuration=_configuration(),
    )
    assert accepted["delivery_id"]
    assert report["production_ready"] is False
    assert report["result"] == "INCOMPLETE"
    assert report["integrity"]["manual_only_delivery_count"] == 1
    assert report["integrity"]["submitted_without_delivery_count"] == 1
    assert report["coverage"]["resend"]["cases"]["delivered"]["passed"] is False


def test_test_environment_never_claims_production_readiness(tmp_path):
    report = LegalDeliveryQualificationEvaluator(_qualified_service(tmp_path)).evaluate(
        "workspace-one", environment="test", provider_configuration=_configuration(),
    )
    assert report["production_ready"] is False
    assert report["result"] == "LOCAL_QUALIFICATION_LOGIC_PASSED"


def test_missing_live_configuration_fails_production_gate(tmp_path):
    report = LegalDeliveryQualificationEvaluator(_qualified_service(tmp_path)).evaluate(
        "workspace-one", environment="production", provider_configuration={},
    )
    assert report["production_ready"] is False
    assert report["configuration_checks"]["resend"]["passed"] is False
    assert report["configuration_checks"]["microsoft_graph"]["missing_scopes"] == [
        "ExchangeMessageTrace.Read.All", "Mail.ReadWrite", "Mail.Send",
    ]


def test_report_is_exclusive_and_digest_detects_tampering(tmp_path):
    evaluator = LegalDeliveryQualificationEvaluator(_qualified_service(tmp_path / "legal"))
    report = evaluator.evaluate(
        "workspace-one", environment="test", provider_configuration=_configuration(),
    )
    output = evaluator.write_report(tmp_path / "report.json", report)
    loaded = json.loads(output.read_text())
    assert evaluator.verify_report(loaded) is True
    loaded["result"] = "PRODUCTION_PROVIDER_CASES_PASSED"
    assert evaluator.verify_report(loaded) is False
    with pytest.raises(
        LegalDeliveryQualificationError, match="delivery_qualification_report_already_exists",
    ):
        evaluator.write_report(output, report)


def test_invalid_environment_and_output_format_fail_closed(tmp_path):
    evaluator = LegalDeliveryQualificationEvaluator(LegalDeliveryService(tmp_path / "legal"))
    with pytest.raises(
        LegalDeliveryQualificationError, match="delivery_qualification_environment_invalid",
    ):
        evaluator.evaluate("workspace-one", environment="live")
    report = evaluator.evaluate("workspace-one", environment="test")
    with pytest.raises(
        LegalDeliveryQualificationError, match="delivery_qualification_report_must_be_json",
    ):
        evaluator.write_report(tmp_path / "report.txt", report)


def test_report_refuses_symbolic_link_destination(tmp_path):
    evaluator = LegalDeliveryQualificationEvaluator(LegalDeliveryService(tmp_path / "legal"))
    report = evaluator.evaluate("workspace-one", environment="test")
    link = tmp_path / "report.json"
    link.symlink_to(tmp_path / "outside.json")
    with pytest.raises(
        LegalDeliveryQualificationError, match="delivery_qualification_report_symlink_refused",
    ):
        evaluator.write_report(link, report)
