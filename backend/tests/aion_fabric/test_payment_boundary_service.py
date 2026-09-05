from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.payment_boundary_service import PaymentBoundaryService


KEY = b"test-webhook-key-not-a-production-secret"


def service(tmp_path):
    return PaymentBoundaryService(tmp_path, webhook_keys={"testpay": KEY})


def proposal(subject, **changes):
    values = dict(billing_id="billing.1", tenant_id="tenant.acme", provider="testpay",
                  customer_vault_ref="vault://payments/customer/acme",
                  payment_method_vault_ref="vault://payments/method/default",
                  plan="boardroom", amount=99, currency="EUR", interval="month",
                  offer_version="2026-09", consent_ref="consent.1", idempotency_key="idem.1")
    values.update(changes)
    return subject.propose(**values)


def event(subject, event_type="subscription_active", signature=None, event_id="event.1"):
    payload = {"provider": "testpay", "event_id": event_id, "event_type": event_type,
               "billing_id": "billing.1", "provider_object_ref": "provider-object-opaque",
               "occurred_at": "2026-09-05T01:00:00+00:00"}
    return subject.accept_provider_event(**payload, signature=signature or subject.sign_test_event(KEY, payload))


def test_only_opaque_vault_references_are_accepted(tmp_path):
    subject = service(tmp_path)
    with pytest.raises(ValueError, match="opaque_vault"):
        proposal(subject, payment_method_vault_ref="4242424242424242")


def test_proposal_is_idempotent_and_conflicts_fail_closed(tmp_path):
    subject = service(tmp_path)
    assert proposal(subject) == proposal(subject)
    with pytest.raises(ValueError, match="idempotency_conflict"):
        proposal(subject, billing_id="billing.2")


def test_approval_binds_exact_visible_terms(tmp_path):
    subject = service(tmp_path)
    proposal(subject)
    with pytest.raises(PermissionError, match="exact_terms_mismatch"):
        subject.approve(billing_id="billing.1", actor_id="owner.1", approval_ref="approval.1",
                        expected_plan="boardroom", expected_amount=100, expected_currency="EUR")
    status = subject.approve(billing_id="billing.1", actor_id="owner.1", approval_ref="approval.1",
                             expected_plan="boardroom", expected_amount=99, expected_currency="EUR")
    assert status["state"] == "approved_pending_provider"
    assert "vault://" not in json.dumps(status)


def test_provider_event_requires_signature_and_is_idempotent(tmp_path):
    subject = service(tmp_path)
    proposal(subject)
    subject.approve(billing_id="billing.1", actor_id="owner.1", approval_ref="approval.1",
                    expected_plan="boardroom", expected_amount=99, expected_currency="EUR")
    with pytest.raises(PermissionError, match="signature_invalid"):
        event(subject, signature="bad")
    first = event(subject)
    assert first == event(subject)
    assert subject.public_status("billing.1")["state"] == "paid_active"


def test_cancellation_is_pending_until_verified_provider_event(tmp_path):
    subject = service(tmp_path)
    proposal(subject)
    pending = subject.cancel(billing_id="billing.1", actor_id="owner.1", cancellation_ref="cancel.1")
    assert pending["state"] == "cancellation_pending_provider"
    event(subject, event_type="subscription_cancelled")
    assert subject.public_status("billing.1")["state"] == "cancelled"


def test_store_contains_no_card_or_provider_secret(tmp_path):
    subject = service(tmp_path)
    proposal(subject)
    stored = subject.path.read_text().lower()
    assert "424242" not in stored
    assert KEY.decode() not in stored
    assert "consent.1" not in stored
