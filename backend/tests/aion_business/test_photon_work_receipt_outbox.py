from __future__ import annotations

import os
import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonLedger,
    PhotonLedgerEntry,
    PhotonPriceBook,
    PhotonWalletEngine,
    build_work_receipt,
)
from backend.modules.aion_business.runtime.photon_work_receipt_outbox import (
    PhotonWorkReceiptOutbox,
    PhotonWorkReceiptOutboxError,
)


def receipt(*, receipt_id="work:one", previous="genesis", photons=25):
    return build_work_receipt(
        receipt_id=receipt_id, tenant_commitment="tenant-commitment-1",
        device_id="node-1", action_type="quote.prepared", outcome_id=f"outcome:{receipt_id}",
        photons=photons, rate_card_version="price-1", reservation_id=f"reservation:{receipt_id}",
        completed_at="2026-10-17T22:00:00Z", previous_receipt_hash=previous,
        success_evidence_code="quote.persisted",
    )


def store(tmp_path, *, max_pending=100):
    key = Ed25519PrivateKey.generate()
    return PhotonWorkReceiptOutbox(
        tmp_path / "node" / "receipt-outbox.sqlite3",
        tenant_commitment="tenant-commitment-1", device_id="node-1",
        device_private_key=key, max_pending=max_pending,
    )


def test_signed_receipt_survives_restart_and_acknowledgement(tmp_path):
    key = Ed25519PrivateKey.generate()
    first = PhotonWorkReceiptOutbox(
        tmp_path / "outbox.sqlite3", tenant_commitment="tenant-commitment-1",
        device_id="node-1", device_private_key=key,
    )
    queued = first.enqueue(receipt(), event_id="enqueue-1", recorded_at="t1")
    assert first.verify(queued) is True
    assert first.status()["pending_count"] == 1
    restarted = PhotonWorkReceiptOutbox(
        tmp_path / "outbox.sqlite3", tenant_commitment="tenant-commitment-1",
        device_id="node-1", device_private_key=key,
    )
    submitted = restarted.mark_submitted(
        "work:one", event_id="submit-1", batch_reference="batch-1", recorded_at="t2"
    )
    assert submitted["outbox"]["state"] == "submitted"
    acknowledged = restarted.acknowledge(
        "work:one", event_id="ack-1", remote_receipt_reference="remote-1",
        recorded_at="t3",
    )
    assert acknowledged["outbox"]["state"] == "acknowledged"
    assert restarted.pending() == []
    assert restarted.status()["pending_count"] == 0


def test_chain_hash_and_identity_are_enforced(tmp_path):
    outbox = store(tmp_path)
    first = outbox.enqueue(receipt(), event_id="enqueue-1", recorded_at="t1")
    second_receipt = receipt(
        receipt_id="work:two", previous=first["receipt"]["receipt_hash"]
    )
    outbox.enqueue(second_receipt, event_id="enqueue-2", recorded_at="t2")
    with pytest.raises(PhotonWorkReceiptOutboxError, match="previous_hash_mismatch"):
        outbox.enqueue(
            receipt(receipt_id="work:three", previous="genesis"),
            event_id="enqueue-3", recorded_at="t3",
        )
    wrong_device = receipt(receipt_id="work:bad", previous=second_receipt["receipt_hash"])
    wrong_device["device_id"] = "node-2"
    with pytest.raises(PhotonWorkReceiptOutboxError, match="device_mismatch"):
        outbox.enqueue(wrong_device, event_id="enqueue-bad", recorded_at="t4")


def test_content_and_local_model_token_fields_are_fail_closed(tmp_path):
    outbox = store(tmp_path)
    with_content = receipt()
    with_content["prompt"] = "private customer instruction"
    with pytest.raises(PhotonWorkReceiptOutboxError, match="fields_invalid"):
        outbox.enqueue(with_content, event_id="enqueue-content", recorded_at="t1")
    billed_tokens = receipt()
    billed_tokens["local_model_tokens_billed"] = True
    with pytest.raises(PhotonWorkReceiptOutboxError, match="model_tokens_prohibited"):
        outbox.enqueue(billed_tokens, event_id="enqueue-token", recorded_at="t1")


def test_outbox_is_bounded_immutable_and_event_idempotent(tmp_path):
    outbox = store(tmp_path, max_pending=1)
    queued = outbox.enqueue(receipt(), event_id="enqueue-1", recorded_at="t1")
    assert outbox.enqueue(receipt(), event_id="enqueue-1", recorded_at="t1") == queued
    with pytest.raises(PhotonWorkReceiptOutboxError, match="capacity_exceeded"):
        outbox.enqueue(
            receipt(receipt_id="work:two", previous=queued["receipt"]["receipt_hash"]),
            event_id="enqueue-2", recorded_at="t2",
        )
    with sqlite3.connect(outbox.path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE photon_work_receipts SET recorded_at = 'changed' WHERE receipt_id = 'work:one'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM photon_work_receipt_outbox_events WHERE event_id = 'enqueue-1'"
            )


def test_signature_tamper_and_terminal_transition_are_rejected(tmp_path):
    outbox = store(tmp_path)
    envelope = outbox.enqueue(receipt(), event_id="enqueue-1", recorded_at="t1")
    tampered = {**envelope, "receipt": {**envelope["receipt"], "photons": 99}}
    with pytest.raises(PhotonWorkReceiptOutboxError, match="signature_invalid"):
        outbox.verify(tampered)
    outbox.reject(
        "work:one", event_id="reject-1", error_code="rate_mismatch", recorded_at="t2"
    )
    with pytest.raises(PhotonWorkReceiptOutboxError, match="terminal"):
        outbox.mark_submitted(
            "work:one", event_id="submit-after-reject", batch_reference="batch-1",
            recorded_at="t3",
        )


def test_successful_wallet_capture_enters_signed_outbox_automatically(tmp_path):
    outbox = store(tmp_path)
    ledger = PhotonLedger()
    ledger.post(
        transaction_id="grant-1", tenant_id="tenant-1", reason="bundle_grant",
        source_receipt_id="purchase-1", rate_card_version="price-1",
        idempotency_key="grant-1", recorded_at="t0",
        entries=[
            PhotonLedgerEntry("platform.grant-liability", -100),
            PhotonLedgerEntry("customer.available", 100),
        ],
    )
    price_book = PhotonPriceBook(
        version="price-1", currency="GBP", minor_units_per_1000_photons=100,
        action_rates={"quote.prepared": 25}, effective_at="2026-10-17T00:00:00Z",
        region="GB", cohort="launch", reason="launch",
    )
    wallet = PhotonWalletEngine(
        ledger, tenant_id="tenant-1", price_book=price_book, receipt_sink=outbox,
    )
    wallet.reserve(
        reservation_id="reservation-1", action_type="quote.prepared", created_at="t1"
    )
    captured = wallet.capture(
        reservation_id="reservation-1", outcome_id="outcome-1", device_id="node-1",
        tenant_commitment="tenant-commitment-1",
        success_evidence_code="quote.persisted", completed_at="t2",
    )
    assert captured["state"] == "captured"
    assert captured["receipt_delivery"]["outbox"]["state"] == "queued"
    assert outbox.pending()[0]["receipt"]["receipt_id"] == "work:reservation-1"


def test_outbox_store_is_private_refuses_symlink_and_revalidates_stored_receipt(tmp_path):
    outbox = store(tmp_path)
    outbox.enqueue(receipt(), event_id="enqueue-1", recorded_at="t1")
    assert os.stat(outbox.path.parent).st_mode & 0o777 == 0o700
    assert os.stat(outbox.path).st_mode & 0o777 == 0o600
    link = tmp_path / "linked-outbox.sqlite3"
    link.symlink_to(outbox.path)
    with pytest.raises(PhotonWorkReceiptOutboxError, match="symlink_database_forbidden"):
        PhotonWorkReceiptOutbox(
            link,
            tenant_commitment="tenant-commitment-1",
            device_id="node-1",
            device_private_key=Ed25519PrivateKey.generate(),
        )
    with sqlite3.connect(outbox.path) as connection:
        connection.execute("DROP TRIGGER photon_work_receipts_no_update")
        connection.execute(
            "UPDATE photon_work_receipts SET receipt_json = '{}' WHERE receipt_id = 'work:one'"
        )
    with pytest.raises(PhotonWorkReceiptOutboxError, match="signature_invalid"):
        outbox.receipt("work:one")
