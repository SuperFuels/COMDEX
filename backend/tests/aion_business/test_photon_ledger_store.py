from __future__ import annotations

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonLedgerEntry,
    PhotonPriceBook,
    PhotonWalletEngine,
)
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore


def post_grant(store, *, transaction_id="tx-1", key="order-1", amount=1000):
    return store.post(
        transaction_id=transaction_id,
        tenant_id="tenant-1",
        reason="paid_bundle_grant",
        source_receipt_id="billing-1",
        rate_card_version="v1",
        idempotency_key=key,
        recorded_at="2026-10-17T20:00:00Z",
        entries=[
            PhotonLedgerEntry("platform.grant-liability", -amount),
            PhotonLedgerEntry("customer.available", amount),
        ],
    )


def test_durable_ledger_posts_once_and_rebuilds_balances(tmp_path):
    store = PhotonLedgerStore(tmp_path / "billing" / "photon.sqlite3")
    first = post_grant(store)
    second = post_grant(store)
    assert second == first
    assert store.transaction("tx-1") == first
    assert store.balances(tenant_id="tenant-1") == {
        "customer.available": 1000,
        "platform.grant-liability": -1000,
    }
    assert store.integrity() == {
        "schema_version": "tessaris.photon-ledger-store.v1",
        "sqlite_integrity": "ok",
        "unbalanced_transaction_ids": [],
        "incomplete_transaction_ids": [],
        "hash_mismatch_transaction_ids": [],
        "transaction_count": 1,
        "entry_count": 2,
        "healthy": True,
    }


def test_idempotency_key_cannot_be_repurposed(tmp_path):
    store = PhotonLedgerStore(tmp_path / "photon.sqlite3")
    post_grant(store)
    with pytest.raises(ValueError, match="idempotency_collision"):
        post_grant(store, transaction_id="tx-2", amount=2000)


def test_ledger_rows_are_database_immutable(tmp_path):
    store = PhotonLedgerStore(tmp_path / "photon.sqlite3")
    post_grant(store)
    with sqlite3.connect(store.path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="photon_ledger_immutable"):
            connection.execute(
                "UPDATE photon_ledger_entries SET quantity_photons = 9 WHERE entry_id = 1"
            )


def test_unbalanced_transaction_never_reaches_database(tmp_path):
    store = PhotonLedgerStore(tmp_path / "photon.sqlite3")
    with pytest.raises(ValueError, match="unbalanced"):
        store.post(
            transaction_id="tx-bad", tenant_id="tenant-1", reason="grant",
            source_receipt_id="billing-bad", rate_card_version="v1",
            idempotency_key="bad", recorded_at="now",
            entries=[PhotonLedgerEntry("a", 10), PhotonLedgerEntry("b", -9)],
        )
    assert store.integrity()["transaction_count"] == 0


def test_wallet_lifecycle_runs_against_durable_store(tmp_path):
    store = PhotonLedgerStore(tmp_path / "photon.sqlite3")
    post_grant(store)
    book = PhotonPriceBook(
        version="v1", currency="GBP", minor_units_per_1000_photons=1000,
        action_rates={"quote.prepared": 25}, effective_at="future",
        region="GB", cohort="pilot", reason="pilot_calibration",
    )
    wallet = PhotonWalletEngine(store, tenant_id="tenant-1", price_book=book)
    wallet.reserve(reservation_id="failed", action_type="quote.prepared", created_at="t1")
    wallet.release(reservation_id="failed", reason_code="outcome_failed", released_at="t2")
    assert wallet.available() == 1000
    wallet.reserve(reservation_id="success", action_type="quote.prepared", created_at="t3")
    captured = wallet.capture(
        reservation_id="success", outcome_id="outcome-1", device_id="device-1",
        tenant_commitment="tenant-hash", success_evidence_code="provider_ack",
        completed_at="t4",
    )
    assert captured["state"] == "captured"
    assert wallet.available() == 975
    assert store.balances(tenant_id="tenant-1")["platform.consumed"] == 25
    assert store.integrity()["healthy"] is True


def test_protected_account_cannot_be_driven_negative(tmp_path):
    store = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    post_grant(store, amount=10)
    with pytest.raises(ValueError, match="protected_account_insufficient"):
        store.post(
            transaction_id="overspend", tenant_id="tenant-1", reason="outcome_reservation",
            source_receipt_id="reservation-1", rate_card_version="v1",
            idempotency_key="overspend", recorded_at="t2",
            entries=[PhotonLedgerEntry("customer.available", -11), PhotonLedgerEntry("customer.reserved", 11)],
            nonnegative_accounts=["customer.available"],
        )
    assert store.balances(tenant_id="tenant-1")["customer.available"] == 10


def test_protected_account_checks_aggregate_transaction_delta(tmp_path):
    store = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    post_grant(store, amount=10)
    with pytest.raises(ValueError, match="protected_account_insufficient"):
        store.post(
            transaction_id="split-overspend", tenant_id="tenant-1", reason="outcome_reservation",
            source_receipt_id="reservation-split", rate_card_version="v1",
            idempotency_key="split-overspend", recorded_at="t2",
            entries=[
                PhotonLedgerEntry("customer.available", -6),
                PhotonLedgerEntry("customer.available", -6),
                PhotonLedgerEntry("customer.reserved", 12),
            ],
            nonnegative_accounts=["customer.available"],
        )
    assert store.balances(tenant_id="tenant-1")["customer.available"] == 10


def test_database_is_private_and_symlink_target_is_rejected(tmp_path):
    store = PhotonLedgerStore(tmp_path / "private" / "ledger.sqlite3")
    assert os.stat(store.path.parent).st_mode & 0o777 == 0o700
    assert os.stat(store.path).st_mode & 0o777 == 0o600
    link = tmp_path / "linked-ledger.sqlite3"
    link.symlink_to(store.path)
    with pytest.raises(ValueError, match="symlink_database_forbidden"):
        PhotonLedgerStore(link)


def test_completed_transaction_rejects_appended_entries(tmp_path):
    store = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    post_grant(store)
    with sqlite3.connect(store.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError, match="transaction_sealed"):
            connection.execute(
                """
                INSERT INTO photon_ledger_entries (
                    transaction_id, position, account, quantity_photons
                ) VALUES ('tx-1', 2, 'customer.available', 1)
                """
            )


def test_concurrent_replay_posts_one_transaction(tmp_path):
    database = tmp_path / "ledger.sqlite3"
    store = PhotonLedgerStore(database)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: post_grant(store), range(24)))
    assert all(result == results[0] for result in results)
    assert store.integrity()["transaction_count"] == 1
    assert store.balances(tenant_id="tenant-1")["customer.available"] == 1000


def test_transaction_identifier_cannot_be_reused_across_idempotency_keys(tmp_path):
    store = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    post_grant(store)
    with pytest.raises(ValueError, match="transaction_id_reused"):
        post_grant(store, transaction_id="tx-1", key="different-order", amount=2000)


def test_integrity_reports_hash_mismatch(tmp_path):
    store = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    post_grant(store)
    with sqlite3.connect(store.path) as connection:
        connection.execute("DROP TRIGGER photon_transactions_no_update")
        connection.execute(
            "UPDATE photon_ledger_transactions SET reason = 'tampered' WHERE transaction_id = 'tx-1'"
        )
    result = store.integrity()
    assert result["hash_mismatch_transaction_ids"] == ["tx-1"]
    assert result["healthy"] is False
    with pytest.raises(ValueError, match="transaction_hash_mismatch"):
        store.transaction("tx-1")


def test_existing_v1_database_is_sealed_without_rewriting_history(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    candidate = PhotonLedgerStore._candidate(
        transaction_id="legacy-tx", tenant_id="tenant-1", reason="paid_bundle_grant",
        source_receipt_id="billing-legacy", rate_card_version="v1",
        idempotency_key="legacy-order", recorded_at="2026-10-17T20:00:00Z",
        entries=[
            PhotonLedgerEntry("platform.grant-liability", -50),
            PhotonLedgerEntry("customer.available", 50),
        ],
    )
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE photon_ledger_transactions (
                transaction_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL, transaction_hash TEXT NOT NULL UNIQUE,
                reason TEXT NOT NULL, source_receipt_id TEXT NOT NULL,
                rate_card_version TEXT NOT NULL, recorded_at TEXT NOT NULL,
                schema_version TEXT NOT NULL, asset_namespace TEXT NOT NULL,
                customer_content_included INTEGER NOT NULL,
                UNIQUE (tenant_id, idempotency_key)
            );
            CREATE TABLE photon_ledger_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL REFERENCES photon_ledger_transactions(transaction_id),
                position INTEGER NOT NULL, account TEXT NOT NULL,
                quantity_photons INTEGER NOT NULL,
                UNIQUE (transaction_id, position)
            );
            CREATE TRIGGER photon_transactions_no_update
                BEFORE UPDATE ON photon_ledger_transactions
                BEGIN SELECT RAISE(ABORT, 'photon_ledger_immutable'); END;
            """
        )
        connection.execute(
            """
            INSERT INTO photon_ledger_transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                candidate["transaction_id"], candidate["tenant_id"],
                candidate["idempotency_key"], candidate["transaction_hash"],
                candidate["reason"], candidate["source_receipt_id"],
                candidate["rate_card_version"], candidate["recorded_at"],
                candidate["schema_version"], candidate["asset_namespace"],
            ),
        )
        connection.executemany(
            """
            INSERT INTO photon_ledger_entries (
                transaction_id, position, account, quantity_photons
            ) VALUES (?, ?, ?, ?)
            """,
            [
                ("legacy-tx", index, row["account"], row["quantity_photons"])
                for index, row in enumerate(candidate["entries"])
            ],
        )
    store = PhotonLedgerStore(database)
    assert store.transaction("legacy-tx") == candidate
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT expected_entry_count FROM photon_ledger_transactions"
        ).fetchone()[0] == 2
