from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonLedger,
    PhotonLedgerEntry,
)


LEDGER_STORE_SCHEMA = "tessaris.photon-ledger-store.v1"


class PhotonLedgerStore:
    """Durable immutable Photon ledger for the hosted billing control plane."""

    def __init__(self, database_path: str | Path) -> None:
        candidate = Path(database_path).expanduser()
        if candidate.is_symlink():
            raise ValueError("photon_ledger_symlink_database_forbidden")
        self.path = candidate.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self._initialise()
        os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS photon_ledger_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    transaction_hash TEXT NOT NULL UNIQUE,
                    reason TEXT NOT NULL,
                    source_receipt_id TEXT NOT NULL,
                    rate_card_version TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    asset_namespace TEXT NOT NULL,
                    customer_content_included INTEGER NOT NULL CHECK (customer_content_included = 0),
                    expected_entry_count INTEGER NOT NULL CHECK (expected_entry_count >= 2),
                    UNIQUE (tenant_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS photon_ledger_entries (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT NOT NULL REFERENCES photon_ledger_transactions(transaction_id),
                    position INTEGER NOT NULL,
                    account TEXT NOT NULL,
                    quantity_photons INTEGER NOT NULL CHECK (quantity_photons != 0),
                    UNIQUE (transaction_id, position)
                );
                CREATE INDEX IF NOT EXISTS idx_photon_entries_account
                    ON photon_ledger_entries(account);
                CREATE INDEX IF NOT EXISTS idx_photon_transactions_tenant
                    ON photon_ledger_transactions(tenant_id, recorded_at, transaction_id);
                CREATE TRIGGER IF NOT EXISTS photon_transactions_no_update
                    BEFORE UPDATE ON photon_ledger_transactions
                    BEGIN SELECT RAISE(ABORT, 'photon_ledger_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_transactions_no_delete
                    BEFORE DELETE ON photon_ledger_transactions
                    BEGIN SELECT RAISE(ABORT, 'photon_ledger_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_entries_no_update
                    BEFORE UPDATE ON photon_ledger_entries
                    BEGIN SELECT RAISE(ABORT, 'photon_ledger_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_entries_no_delete
                    BEFORE DELETE ON photon_ledger_entries
                    BEGIN SELECT RAISE(ABORT, 'photon_ledger_immutable'); END;
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(photon_ledger_transactions)"
                ).fetchall()
            }
            if "expected_entry_count" not in columns:
                invalid = connection.execute(
                    """
                    SELECT t.transaction_id
                    FROM photon_ledger_transactions t
                    LEFT JOIN photon_ledger_entries e ON e.transaction_id = t.transaction_id
                    GROUP BY t.transaction_id HAVING COUNT(e.entry_id) < 2
                    LIMIT 1
                    """
                ).fetchone()
                if invalid:
                    raise ValueError("photon_legacy_ledger_entry_count_invalid")
                connection.execute("DROP TRIGGER IF EXISTS photon_transactions_no_update")
                connection.execute(
                    """
                    ALTER TABLE photon_ledger_transactions
                    ADD COLUMN expected_entry_count INTEGER NOT NULL DEFAULT 2
                    CHECK (expected_entry_count >= 2)
                    """
                )
                connection.execute(
                    """
                    UPDATE photon_ledger_transactions
                    SET expected_entry_count = (
                        SELECT COUNT(*) FROM photon_ledger_entries e
                        WHERE e.transaction_id = photon_ledger_transactions.transaction_id
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TRIGGER photon_transactions_no_update
                    BEFORE UPDATE ON photon_ledger_transactions
                    BEGIN SELECT RAISE(ABORT, 'photon_ledger_immutable'); END
                    """
                )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS photon_entries_no_excess_insert
                BEFORE INSERT ON photon_ledger_entries
                WHEN (
                    SELECT COUNT(*) FROM photon_ledger_entries
                    WHERE transaction_id = NEW.transaction_id
                ) >= (
                    SELECT expected_entry_count FROM photon_ledger_transactions
                    WHERE transaction_id = NEW.transaction_id
                )
                BEGIN SELECT RAISE(ABORT, 'photon_ledger_transaction_sealed'); END
                """
            )

    @staticmethod
    def _candidate(
        *,
        transaction_id: str,
        tenant_id: str,
        reason: str,
        source_receipt_id: str,
        rate_card_version: str,
        idempotency_key: str,
        recorded_at: str,
        entries: Iterable[PhotonLedgerEntry],
    ) -> dict[str, Any]:
        validator = PhotonLedger()
        return validator.post(
            transaction_id=transaction_id,
            tenant_id=tenant_id,
            reason=reason,
            source_receipt_id=source_receipt_id,
            rate_card_version=rate_card_version,
            idempotency_key=idempotency_key,
            recorded_at=recorded_at,
            entries=entries,
        )

    def post(
        self,
        *,
        transaction_id: str,
        tenant_id: str,
        reason: str,
        source_receipt_id: str,
        rate_card_version: str,
        idempotency_key: str,
        recorded_at: str,
        entries: Iterable[PhotonLedgerEntry],
        nonnegative_accounts: Iterable[str] = (),
    ) -> dict[str, Any]:
        candidate = self._candidate(
            transaction_id=transaction_id,
            tenant_id=tenant_id,
            reason=reason,
            source_receipt_id=source_receipt_id,
            rate_card_version=rate_card_version,
            idempotency_key=idempotency_key,
            recorded_at=recorded_at,
            entries=entries,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                reused_transaction = connection.execute(
                    """
                    SELECT transaction_hash
                    FROM photon_ledger_transactions
                    WHERE transaction_id = ?
                    """,
                    (candidate["transaction_id"],),
                ).fetchone()
                if reused_transaction:
                    if reused_transaction["transaction_hash"] != candidate["transaction_hash"]:
                        raise ValueError("ledger_transaction_id_reused")
                    result = self._read_transaction(connection, candidate["transaction_id"])
                    connection.commit()
                    return result
                existing = connection.execute(
                    """
                    SELECT transaction_id, transaction_hash
                    FROM photon_ledger_transactions
                    WHERE tenant_id = ? AND idempotency_key = ?
                    """,
                    (tenant_id, idempotency_key),
                ).fetchone()
                if existing:
                    if existing["transaction_hash"] != candidate["transaction_hash"]:
                        raise ValueError("ledger_idempotency_collision")
                    result = self._read_transaction(connection, existing["transaction_id"])
                    connection.commit()
                    return result
                protected = set(nonnegative_accounts)
                protected_deltas: dict[str, int] = {}
                for entry in candidate["entries"]:
                    account = entry["account"]
                    if account in protected:
                        protected_deltas[account] = protected_deltas.get(account, 0) + int(
                            entry["quantity_photons"]
                        )
                for account, delta in protected_deltas.items():
                    current = connection.execute(
                        """
                        SELECT COALESCE(SUM(e.quantity_photons), 0)
                        FROM photon_ledger_entries e
                        JOIN photon_ledger_transactions t ON t.transaction_id = e.transaction_id
                        WHERE t.tenant_id = ? AND e.account = ?
                        """,
                        (tenant_id, account),
                    ).fetchone()[0]
                    if int(current) + delta < 0:
                        raise ValueError("ledger_protected_account_insufficient")
                connection.execute(
                    """
                    INSERT INTO photon_ledger_transactions (
                        transaction_id, tenant_id, idempotency_key, transaction_hash,
                        reason, source_receipt_id, rate_card_version, recorded_at,
                        schema_version, asset_namespace, customer_content_included,
                        expected_entry_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        candidate["transaction_id"],
                        candidate["tenant_id"],
                        candidate["idempotency_key"],
                        candidate["transaction_hash"],
                        candidate["reason"],
                        candidate["source_receipt_id"],
                        candidate["rate_card_version"],
                        candidate["recorded_at"],
                        candidate["schema_version"],
                        candidate["asset_namespace"],
                        len(candidate["entries"]),
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO photon_ledger_entries (
                        transaction_id, position, account, quantity_photons
                    ) VALUES (?, ?, ?, ?)
                    """,
                    [
                        (
                            candidate["transaction_id"],
                            position,
                            entry["account"],
                            entry["quantity_photons"],
                        )
                        for position, entry in enumerate(candidate["entries"])
                    ],
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return candidate

    def transaction(self, transaction_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            return self._read_transaction(connection, transaction_id)

    @staticmethod
    def _read_transaction(
        connection: sqlite3.Connection, transaction_id: str
    ) -> dict[str, Any]:
        transaction = connection.execute(
            "SELECT * FROM photon_ledger_transactions WHERE transaction_id = ?",
            (transaction_id,),
        ).fetchone()
        if not transaction:
            raise KeyError("ledger_transaction_not_found")
        entries = connection.execute(
            """
            SELECT account, quantity_photons
            FROM photon_ledger_entries
            WHERE transaction_id = ? ORDER BY position
            """,
            (transaction_id,),
        ).fetchall()
        if len(entries) != int(transaction["expected_entry_count"]):
            raise ValueError("photon_ledger_entry_count_mismatch")
        result = {
            "schema_version": transaction["schema_version"],
            "asset_namespace": transaction["asset_namespace"],
            "transaction_id": transaction["transaction_id"],
            "tenant_id": transaction["tenant_id"],
            "reason": transaction["reason"],
            "source_receipt_id": transaction["source_receipt_id"],
            "rate_card_version": transaction["rate_card_version"],
            "idempotency_key": transaction["idempotency_key"],
            "recorded_at": transaction["recorded_at"],
            "entries": [
                {"account": row["account"], "quantity_photons": row["quantity_photons"]}
                for row in entries
            ],
            "customer_content_included": False,
            "transaction_hash": transaction["transaction_hash"],
        }
        unsigned = {key: value for key, value in result.items() if key != "transaction_hash"}
        if hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest() != result["transaction_hash"]:
            raise ValueError("photon_ledger_transaction_hash_mismatch")
        return result

    def balances(self, *, tenant_id: str) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.account, SUM(e.quantity_photons) AS balance
                FROM photon_ledger_entries e
                JOIN photon_ledger_transactions t ON t.transaction_id = e.transaction_id
                WHERE t.tenant_id = ?
                GROUP BY e.account ORDER BY e.account
                """,
                (tenant_id,),
            ).fetchall()
        return {row["account"]: int(row["balance"]) for row in rows}

    def wallet_state(self, *, tenant_id: str) -> dict[str, Any]:
        """Return one consistent, content-free tenant view for signed wallet snapshots."""
        with self._connect() as connection:
            connection.execute("BEGIN")
            rows = connection.execute(
                """
                SELECT e.account, SUM(e.quantity_photons) AS balance
                FROM photon_ledger_entries e
                JOIN photon_ledger_transactions t ON t.transaction_id = e.transaction_id
                WHERE t.tenant_id = ?
                GROUP BY e.account ORDER BY e.account
                """,
                (tenant_id,),
            ).fetchall()
            transactions = connection.execute(
                """
                SELECT transaction_id, transaction_hash
                FROM photon_ledger_transactions
                WHERE tenant_id = ? ORDER BY recorded_at, transaction_id
                """,
                (tenant_id,),
            ).fetchall()
            connection.commit()
        balances = {row["account"]: int(row["balance"]) for row in rows}
        anchor_input = [
            {"transaction_id": row["transaction_id"], "transaction_hash": row["transaction_hash"]}
            for row in transactions
        ]
        anchor = hashlib.sha256(
            json.dumps(anchor_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        reserved = sum(
            quantity
            for account, quantity in balances.items()
            if account == "customer.reserved"
            or (account.startswith("offline.") and account.endswith(".reserved"))
        )
        return {
            "tenant_id": tenant_id,
            "available_photons": int(balances.get("customer.available", 0)),
            "reserved_photons": int(reserved),
            "lifetime_consumed_photons": int(balances.get("platform.consumed", 0)),
            "ledger_transaction_count": len(anchor_input),
            "ledger_anchor": anchor,
            "customer_content_included": False,
        }

    def activity(self, *, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Return bounded content-free ledger activity for one authenticated tenant."""
        limit = int(limit)
        if not 1 <= limit <= 200:
            raise ValueError("photon_activity_limit_invalid")
        with self._connect() as connection:
            transactions = connection.execute(
                """
                SELECT * FROM photon_ledger_transactions
                WHERE tenant_id = ?
                ORDER BY recorded_at DESC, transaction_id DESC LIMIT ?
                """,
                (tenant_id, limit),
            ).fetchall()
            result = []
            for transaction in transactions:
                entries = connection.execute(
                    """
                    SELECT account, quantity_photons FROM photon_ledger_entries
                    WHERE transaction_id = ? ORDER BY position
                    """,
                    (transaction["transaction_id"],),
                ).fetchall()
                result.append(
                    {
                        "transaction_id": transaction["transaction_id"],
                        "reason": transaction["reason"],
                        "source_receipt_id": transaction["source_receipt_id"],
                        "rate_card_version": transaction["rate_card_version"],
                        "recorded_at": transaction["recorded_at"],
                        "entries": [
                            {
                                "account": entry["account"],
                                "quantity_photons": int(entry["quantity_photons"]),
                            }
                            for entry in entries
                        ],
                        "customer_content_included": False,
                    }
                )
        return result

    def integrity(self) -> dict[str, Any]:
        with self._connect() as connection:
            sqlite_status = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            unbalanced = connection.execute(
                """
                SELECT t.transaction_id, SUM(e.quantity_photons) AS total
                FROM photon_ledger_transactions t
                JOIN photon_ledger_entries e ON e.transaction_id = t.transaction_id
                GROUP BY t.transaction_id HAVING total != 0
                """
            ).fetchall()
            incomplete = connection.execute(
                """
                SELECT t.transaction_id
                FROM photon_ledger_transactions t
                LEFT JOIN photon_ledger_entries e ON e.transaction_id = t.transaction_id
                GROUP BY t.transaction_id, t.expected_entry_count
                HAVING COUNT(e.entry_id) != t.expected_entry_count
                """
            ).fetchall()
            incomplete_ids = {row["transaction_id"] for row in incomplete}
            transaction_ids = connection.execute(
                "SELECT transaction_id FROM photon_ledger_transactions ORDER BY transaction_id"
            ).fetchall()
            hash_mismatches: list[str] = []
            for row in transaction_ids:
                transaction_id = str(row["transaction_id"])
                if transaction_id in incomplete_ids:
                    continue
                try:
                    self._read_transaction(connection, transaction_id)
                except ValueError as exc:
                    if str(exc) == "photon_ledger_transaction_hash_mismatch":
                        hash_mismatches.append(transaction_id)
                    else:
                        raise
            counts = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM photon_ledger_transactions) AS transactions,
                    (SELECT COUNT(*) FROM photon_ledger_entries) AS entries
                """
            ).fetchone()
        return {
            "schema_version": LEDGER_STORE_SCHEMA,
            "sqlite_integrity": sqlite_status,
            "unbalanced_transaction_ids": [row["transaction_id"] for row in unbalanced],
            "incomplete_transaction_ids": [row["transaction_id"] for row in incomplete],
            "hash_mismatch_transaction_ids": hash_mismatches,
            "transaction_count": int(counts["transactions"]),
            "entry_count": int(counts["entries"]),
            "healthy": (
                sqlite_status == "ok"
                and not unbalanced
                and not incomplete
                and not hash_mismatches
            ),
        }
