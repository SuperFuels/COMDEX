from __future__ import annotations

import json
import hashlib
import hmac
import os

import pytest

from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_billing_contracts import PhotonLedgerEntry
from backend.modules.aion_business.runtime.photon_revolut_fulfillment import (
    PhotonRevolutFulfilment,
    RevolutHmacWebhookVerifier,
)


class Verifier:
    def verify(self, raw_body, headers):
        return headers.get("signature") == "valid" and bool(raw_body)


class Orders:
    def __init__(self, state="completed", amount=1000, currency="GBP", reference="ref-1"):
        self.state, self.amount, self.currency, self.reference = state, amount, currency, reference

    def retrieve_order(self, order_id):
        return {
            "id": order_id, "external_reference": self.reference,
            "amount_minor": self.amount, "currency": self.currency,
            "state": self.state, "updated_at": "2026-10-17T22:00:00Z",
        }


class Refunds:
    def __init__(self, *, amount=1000, state="completed", currency="GBP", order_id="order-1"):
        self.amount, self.state, self.currency, self.order_id = amount, state, currency, order_id

    def retrieve_refund(self, refund_id):
        return {
            "id": refund_id, "order_id": self.order_id, "amount_minor": self.amount,
            "currency": self.currency, "state": self.state,
            "updated_at": "2026-10-17T23:00:00Z",
        }


class Disputes:
    def __init__(
        self,
        *,
        amount=1000,
        liability_outcome="merchant_lost",
        state="closed",
        currency="GBP",
        order_id="order-1",
    ):
        self.amount = amount
        self.liability_outcome = liability_outcome
        self.state = state
        self.currency = currency
        self.order_id = order_id

    def retrieve_dispute(self, dispute_id):
        return {
            "id": dispute_id,
            "order_id": self.order_id,
            "amount_minor": self.amount,
            "currency": self.currency,
            "state": self.state,
            "liability_outcome": self.liability_outcome,
            "updated_at": "2026-10-18T00:00:00Z",
        }


def service(tmp_path):
    ledger = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    result = PhotonRevolutFulfilment(tmp_path / "fulfilment.sqlite3", ledger=ledger)
    result.record_checkout_intent(
        order_id="order-1", external_reference="ref-1", tenant_id="tenant-1",
        product_id="bundle-100", photons=100, amount_minor=1000, currency="GBP",
        price_book_version="v1", created_at="2026-10-17T21:00:00Z",
    )
    return result, ledger


def webhook(event_id="event-1"):
    return json.dumps(
        {"event": "ORDER_COMPLETED", "order_id": "order-1", "merchant_order_ext_ref": event_id},
        separators=(",", ":"),
    ).encode()


def refund_webhook(refund_id="refund-1"):
    return json.dumps(
        {"event": "REFUND_COMPLETED", "order_id": "order-1", "refund_id": refund_id},
        separators=(",", ":"),
    ).encode()


def dispute_webhook(dispute_id="dispute-1"):
    return json.dumps(
        {"event": "DISPUTE_UPDATED", "order_id": "order-1", "dispute_id": dispute_id},
        separators=(",", ":"),
    ).encode()


def test_paid_order_grants_once_and_replay_is_safe(tmp_path):
    fulfilment, ledger = service(tmp_path)
    first = fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    second = fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    assert first["status"] == "fulfilled" and first["photons_granted"] == 100
    assert second["status"] == "fulfilled" and second["replay"] is True
    assert second["photons_granted"] == 100
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 100
    assert ledger.integrity()["transaction_count"] == 1


def test_billing_records_are_hashed_refund_aware_and_tenant_isolated(tmp_path):
    fulfilment, _ = service(tmp_path)
    fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    original = fulfilment.billing_records(tenant_id="tenant-1")
    assert len(original) == 1
    assert original[0]["amount_minor"] == 1000
    assert original[0]["refunded_minor"] == 0
    assert original[0]["tax_invoice"] is False
    assert original[0]["customer_content_included"] is False
    assert len(original[0]["record_hash"]) == 64
    assert fulfilment.billing_records(tenant_id="tenant-2") == []

    fulfilment.handle_refund_webhook(
        refund_webhook(), {"signature": "valid"},
        verifier=Verifier(), refunds=Refunds(),
    )
    refunded = fulfilment.billing_records(tenant_id="tenant-1")
    assert refunded[0]["refunded_minor"] == 1000
    assert refunded[0]["photons_reversed"] == 100
    assert refunded[0]["record_hash"] != original[0]["record_hash"]


def test_nonterminal_event_grants_nothing_then_later_event_can_fulfil(tmp_path):
    fulfilment, ledger = service(tmp_path)
    pending = fulfilment.handle_webhook(
        webhook("event-pending"), {"signature": "valid"},
        verifier=Verifier(), orders=Orders(state="pending"),
    )
    assert pending["photons_granted"] == 0
    assert ledger.integrity()["transaction_count"] == 0
    completed = fulfilment.handle_webhook(
        webhook("event-complete"), {"signature": "valid"},
        verifier=Verifier(), orders=Orders(state="completed"),
    )
    assert completed["photons_granted"] == 100


def test_webhook_signature_and_authoritative_order_must_match(tmp_path):
    fulfilment, ledger = service(tmp_path)
    with pytest.raises(PermissionError, match="signature_invalid"):
        fulfilment.handle_webhook(
            webhook(), {"signature": "bad"}, verifier=Verifier(), orders=Orders()
        )
    with pytest.raises(PermissionError, match="amount_minor"):
        fulfilment.handle_webhook(
            webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders(amount=999)
        )
    assert ledger.integrity()["transaction_count"] == 0


def test_wrong_event_type_and_oversized_body_are_rejected_before_fulfilment(tmp_path):
    fulfilment, ledger = service(tmp_path)
    wrong = json.dumps(
        {"event": "ORDER_CANCELLED", "order_id": "order-1"}, separators=(",", ":")
    ).encode()
    with pytest.raises(ValueError, match="order_event_type_invalid"):
        fulfilment.handle_webhook(
            wrong, {"signature": "valid"}, verifier=Verifier(), orders=Orders()
        )
    with pytest.raises(ValueError, match="webhook_size_invalid"):
        fulfilment.handle_webhook(
            b"x" * 1_048_577,
            {"signature": "valid"},
            verifier=Verifier(),
            orders=Orders(),
        )
    assert ledger.integrity()["transaction_count"] == 0


def test_fulfilment_store_is_private_and_symlink_target_is_rejected(tmp_path):
    ledger = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    store = PhotonRevolutFulfilment(
        tmp_path / "private" / "fulfilment.sqlite3", ledger=ledger
    )
    assert os.stat(store.path.parent).st_mode & 0o777 == 0o700
    assert os.stat(store.path).st_mode & 0o777 == 0o600
    link = tmp_path / "linked-fulfilment.sqlite3"
    link.symlink_to(store.path)
    with pytest.raises(ValueError, match="symlink_database_forbidden"):
        PhotonRevolutFulfilment(link, ledger=ledger)


def test_checkout_snapshot_is_immutable_and_identity_bound(tmp_path):
    fulfilment, _ = service(tmp_path)
    with pytest.raises(ValueError, match="identity_reused"):
        fulfilment.record_checkout_intent(
            order_id="order-1", external_reference="ref-1", tenant_id="tenant-1",
            product_id="bundle-100", photons=200, amount_minor=1000, currency="GBP",
            price_book_version="v1", created_at="2026-10-17T21:00:00Z",
        )


def test_official_hmac_verifier_uses_raw_body_timestamp_and_rotation_signatures():
    raw = webhook()
    timestamp = "1000000"
    material = b"v1." + timestamp.encode() + b"." + raw
    signature = "v1=" + hmac.new(b"secret", material, hashlib.sha256).hexdigest()
    verifier = RevolutHmacWebhookVerifier(
        "secret", now_milliseconds=lambda: 1000000
    )
    headers = {
        "Revolut-Request-Timestamp": timestamp,
        "Revolut-Signature": f"v1=old-rotating-secret,{signature}",
    }
    assert verifier.verify(raw, headers) is True
    assert verifier.verify(raw + b" ", headers) is False
    expired = RevolutHmacWebhookVerifier(
        "secret", now_milliseconds=lambda: 1000000 + 301000
    )
    assert expired.verify(raw, headers) is False


def test_completed_refund_reverses_grant_once_and_replay_is_safe(tmp_path):
    fulfilment, ledger = service(tmp_path)
    fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    first = fulfilment.handle_refund_webhook(
        refund_webhook(), {"signature": "valid"}, verifier=Verifier(), refunds=Refunds()
    )
    replay = fulfilment.handle_refund_webhook(
        refund_webhook(), {"signature": "valid"}, verifier=Verifier(), refunds=Refunds()
    )
    assert first["status"] == "reversed" and first["photons_reversed"] == 100
    assert replay["status"] == "reversed" and replay["replay"] is True
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 0
    assert ledger.balances(tenant_id="tenant-1")["platform.grant-liability"] == 0
    assert ledger.integrity()["transaction_count"] == 2


def test_partial_refunds_reverse_only_cumulative_proportional_photons(tmp_path):
    fulfilment, ledger = service(tmp_path)
    fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    first = fulfilment.handle_refund_webhook(
        refund_webhook("refund-1"), {"signature": "valid"},
        verifier=Verifier(), refunds=Refunds(amount=250),
    )
    second = fulfilment.handle_refund_webhook(
        refund_webhook("refund-2"), {"signature": "valid"},
        verifier=Verifier(), refunds=Refunds(amount=250),
    )
    assert first["photons_reversed"] == 25
    assert second["photons_reversed"] == 25
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 50


def test_spent_photons_make_refund_manual_review_instead_of_negative_balance(tmp_path):
    fulfilment, ledger = service(tmp_path)
    fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    ledger.post(
        transaction_id="spend-1", tenant_id="tenant-1", reason="verified_outcome_capture",
        source_receipt_id="outcome-1", rate_card_version="v1", idempotency_key="spend-1",
        recorded_at="2026-10-17T22:30:00Z",
        entries=[
            PhotonLedgerEntry("customer.available", -60),
            PhotonLedgerEntry("platform.consumed", 60),
        ],
        nonnegative_accounts=["customer.available"],
    )
    pending = fulfilment.handle_refund_webhook(
        refund_webhook(), {"signature": "valid"}, verifier=Verifier(), refunds=Refunds()
    )
    assert pending["status"] == "manual_review_required"
    assert pending["photon_target"] == 100 and pending["photons_reversed"] == 0
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 40
    assert ledger.integrity()["transaction_count"] == 2

    ledger.post(
        transaction_id="manual-credit", tenant_id="tenant-1", reason="approved_refund_recovery",
        source_receipt_id="refund-1", rate_card_version="v1",
        idempotency_key="manual-credit", recorded_at="2026-10-17T23:30:00Z",
        entries=[
            PhotonLedgerEntry("platform.manual-adjustment", -100),
            PhotonLedgerEntry("customer.available", 100),
        ],
    )
    resolved = fulfilment.resolve_refund(
        "refund-1", recorded_at="2026-10-17T23:31:00Z"
    )
    assert resolved["status"] == "reversed" and resolved["photons_reversed"] == 100
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 40


def test_refund_must_be_terminal_authoritative_and_within_original_order(tmp_path):
    fulfilment, ledger = service(tmp_path)
    fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    awaiting = fulfilment.handle_refund_webhook(
        refund_webhook(), {"signature": "valid"}, verifier=Verifier(),
        refunds=Refunds(state="pending"),
    )
    assert awaiting["status"] == "awaiting_terminal_refund_state"
    with pytest.raises(PermissionError, match="order_id"):
        fulfilment.handle_refund_webhook(
            refund_webhook(), {"signature": "valid"}, verifier=Verifier(),
            refunds=Refunds(order_id="other-order"),
        )
    with pytest.raises(ValueError, match="exceeds_order"):
        fulfilment.handle_refund_webhook(
            refund_webhook("refund-too-large"), {"signature": "valid"},
            verifier=Verifier(), refunds=Refunds(amount=1001),
        )
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 100


def test_final_lost_dispute_reverses_grant_once_and_updates_billing_evidence(tmp_path):
    fulfilment, ledger = service(tmp_path)
    fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    first = fulfilment.handle_dispute_webhook(
        dispute_webhook(), {"signature": "valid"},
        verifier=Verifier(), disputes=Disputes(),
    )
    replay = fulfilment.handle_dispute_webhook(
        dispute_webhook(), {"signature": "valid"},
        verifier=Verifier(), disputes=Disputes(),
    )
    assert first["status"] == "reversed" and first["photons_reversed"] == 100
    assert replay["status"] == "reversed" and replay["replay"] is True
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 0
    status = fulfilment.commercial_status(tenant_id="tenant-1")
    assert status["commercial_hold"] is False
    record = fulfilment.billing_records(tenant_id="tenant-1")[0]
    assert record["disputed_minor"] == 1000
    assert record["photons_dispute_reversed"] == 100
    assert record["commercial_hold"] is False


def test_spent_photons_put_final_dispute_on_hold_until_approved_recovery(tmp_path):
    fulfilment, ledger = service(tmp_path)
    fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    ledger.post(
        transaction_id="spend-dispute", tenant_id="tenant-1",
        reason="verified_outcome_capture", source_receipt_id="outcome-dispute",
        rate_card_version="v1", idempotency_key="spend-dispute",
        recorded_at="2026-10-17T22:30:00Z",
        entries=[
            PhotonLedgerEntry("customer.available", -60),
            PhotonLedgerEntry("platform.consumed", 60),
        ],
        nonnegative_accounts=["customer.available"],
    )
    pending = fulfilment.handle_dispute_webhook(
        dispute_webhook(), {"signature": "valid"},
        verifier=Verifier(), disputes=Disputes(),
    )
    assert pending["status"] == "manual_review_required"
    assert pending["commercial_hold"] is True
    status = fulfilment.commercial_status(tenant_id="tenant-1")
    assert status == {
        "tenant_id": "tenant-1",
        "commercial_hold": True,
        "unresolved_dispute_count": 1,
        "disputed_minor": 1000,
        "photons_pending_reversal": 100,
        "customer_content_included": False,
    }
    assert fulfilment.billing_records(tenant_id="tenant-1")[0]["commercial_hold"] is True

    ledger.post(
        transaction_id="dispute-recovery", tenant_id="tenant-1",
        reason="approved_dispute_recovery", source_receipt_id="dispute-1",
        rate_card_version="v1", idempotency_key="dispute-recovery",
        recorded_at="2026-10-18T00:30:00Z",
        entries=[
            PhotonLedgerEntry("platform.manual-adjustment", -100),
            PhotonLedgerEntry("customer.available", 100),
        ],
    )
    resolved = fulfilment.resolve_dispute(
        "dispute-1", recorded_at="2026-10-18T00:31:00Z"
    )
    assert resolved["status"] == "reversed"
    assert fulfilment.commercial_status(tenant_id="tenant-1")["commercial_hold"] is False
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 40


def test_dispute_requires_authoritative_normalized_outcome_and_cannot_double_debit_refund(tmp_path):
    fulfilment, ledger = service(tmp_path)
    fulfilment.handle_webhook(
        webhook(), {"signature": "valid"}, verifier=Verifier(), orders=Orders()
    )
    pending = fulfilment.handle_dispute_webhook(
        dispute_webhook(), {"signature": "valid"}, verifier=Verifier(),
        disputes=Disputes(liability_outcome="pending"),
    )
    assert pending["status"] == "awaiting_terminal_dispute_state"
    won = fulfilment.handle_dispute_webhook(
        dispute_webhook("dispute-won"), {"signature": "valid"}, verifier=Verifier(),
        disputes=Disputes(liability_outcome="merchant_won"),
    )
    assert won["status"] == "closed_no_debit"
    with pytest.raises(ValueError, match="outcome_invalid"):
        fulfilment.handle_dispute_webhook(
            dispute_webhook("dispute-unknown"), {"signature": "valid"},
            verifier=Verifier(), disputes=Disputes(liability_outcome="provider_mystery"),
        )
    fulfilment.handle_refund_webhook(
        refund_webhook(), {"signature": "valid"},
        verifier=Verifier(), refunds=Refunds(),
    )
    with pytest.raises(ValueError, match="exceeds_order"):
        fulfilment.handle_dispute_webhook(
            dispute_webhook("dispute-after-refund"), {"signature": "valid"},
            verifier=Verifier(), disputes=Disputes(amount=1),
        )
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 0
