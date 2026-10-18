from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonLedger,
    PhotonLedgerEntry,
    PhotonPriceBook,
    PhotonWalletEngine,
    build_work_receipt,
    sign_price_book,
    verify_price_book,
)
from backend.modules.aion_fabric.identity import DeviceIdentity


def price_book():
    return PhotonPriceBook(
        version="2026.10.17-1",
        currency="GBP",
        minor_units_per_1000_photons=1000,
        action_rates={"quote.prepared": 25, "invoice.reconciled": 100},
        effective_at="2026-11-01T00:00:00+00:00",
        region="GB",
        cohort="pilot",
        reason="pilot_price_calibration",
    )


def test_price_preview_is_exact_and_does_not_publish():
    preview = price_book().preview()
    assert preview["published"] is False
    assert preview["minor_units_per_1000_photons"] == 1000
    rows = {item["action_type"]: item for item in preview["outcomes"]}
    assert rows["quote.prepared"]["approximate_minor_units"] == 25
    assert rows["invoice.reconciled"]["approximate_minor_units"] == 100


def test_price_book_is_signed_and_tampering_fails():
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    envelope = sign_price_book(price_book(), identity)
    assert verify_price_book(envelope) is True
    envelope["payload"]["minor_units_per_1000_photons"] = 1
    assert verify_price_book(envelope) is False


def test_double_entry_ledger_conserves_photons_and_is_idempotent():
    ledger = PhotonLedger()
    transaction = ledger.post(
        transaction_id="tx-grant-1",
        tenant_id="tenant-1",
        reason="paid_bundle_grant",
        source_receipt_id="billing-receipt-1",
        rate_card_version="2026.10.17-1",
        idempotency_key="revolut-order-1",
        recorded_at="2026-10-17T20:00:00+00:00",
        entries=[
            PhotonLedgerEntry("platform.grant-liability", -1000),
            PhotonLedgerEntry("customer.available", 1000),
        ],
    )
    duplicate = ledger.post(
        transaction_id="tx-grant-1",
        tenant_id="tenant-1",
        reason="paid_bundle_grant",
        source_receipt_id="billing-receipt-1",
        rate_card_version="2026.10.17-1",
        idempotency_key="revolut-order-1",
        recorded_at="2026-10-17T20:00:00+00:00",
        entries=[
            PhotonLedgerEntry("platform.grant-liability", -1000),
            PhotonLedgerEntry("customer.available", 1000),
        ],
    )
    assert duplicate["transaction_hash"] == transaction["transaction_hash"]
    assert len(ledger.export()) == 1
    assert sum(ledger.balances().values()) == 0
    assert ledger.balances()["customer.available"] == 1000


def test_unbalanced_or_repurposed_idempotency_is_rejected():
    ledger = PhotonLedger()
    with pytest.raises(ValueError, match="unbalanced"):
        ledger.post(
            transaction_id="tx-1", tenant_id="tenant-1", reason="grant",
            source_receipt_id="receipt-1", rate_card_version="v1",
            idempotency_key="key-1", recorded_at="now",
            entries=[PhotonLedgerEntry("customer.available", 10), PhotonLedgerEntry("platform", -9)],
        )


def test_work_receipt_contains_no_prompt_or_customer_content():
    receipt = build_work_receipt(
        receipt_id="receipt-1",
        tenant_commitment="commitment-1",
        device_id="device-1",
        action_type="quote.prepared",
        outcome_id="outcome-1",
        photons=25,
        rate_card_version="v1",
        reservation_id="reservation-1",
        completed_at="2026-10-17T20:00:00+00:00",
        previous_receipt_hash="genesis",
        success_evidence_code="provider_acknowledged",
    )
    assert receipt["customer_content_included"] is False
    assert receipt["local_model_tokens_billed"] is False
    assert "prompt" not in receipt
    assert "message" not in receipt


def test_reserve_capture_release_and_parent_inclusion_do_not_double_charge():
    ledger = PhotonLedger()
    ledger.post(
        transaction_id="grant-1", tenant_id="tenant-1", reason="included_allowance_grant",
        source_receipt_id="grant-receipt-1", rate_card_version="2026.10.17-1",
        idempotency_key="grant-1", recorded_at="start",
        entries=[PhotonLedgerEntry("platform.allowance", -1000), PhotonLedgerEntry("customer.available", 1000)],
    )
    wallet = PhotonWalletEngine(ledger, tenant_id="tenant-1", price_book=price_book())
    wallet.reserve(reservation_id="r-1", action_type="quote.prepared", created_at="t1")
    assert wallet.available() == 975
    wallet.release(reservation_id="r-1", reason_code="outcome_failed", released_at="t2")
    assert wallet.available() == 1000

    wallet.reserve(reservation_id="r-2", action_type="quote.prepared", created_at="t3")
    captured = wallet.capture(
        reservation_id="r-2", outcome_id="o-2", device_id="device-1",
        tenant_commitment="tenant-hash", success_evidence_code="saved_and_verified",
        completed_at="t4",
    )
    assert captured["state"] == "captured"
    assert wallet.available() == 975
    assert ledger.balances(tenant_id="tenant-1")["platform.consumed"] == 25

    child = wallet.reserve(
        reservation_id="r-child", action_type="quote.prepared", created_at="t5",
        billing_parent_id="r-2", included_in_parent=True,
    )
    assert child["photons"] == 0
    assert child["state"] == "included"
    assert wallet.available() == 975
