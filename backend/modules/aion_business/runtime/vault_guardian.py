from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.modules.aion_business.runtime.business_vault import BusinessVaultLayout


GUARDIAN_SCHEMA = "tessaris.vault-guardian.v1"
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAX_RECORD_BYTES = 4 * 1024 * 1024


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: Any) -> str:
    raw = value if isinstance(value, bytes) else _canonical(value)
    return hashlib.sha256(raw).hexdigest()


class VaultGuardianError(ValueError):
    pass


class VaultGuardian:
    """Narrow encrypted semantic record boundary for one external Business Vault."""

    def __init__(
        self,
        layout: BusinessVaultLayout,
        *,
        business_stable_id: str,
        encryption_key: bytes,
    ) -> None:
        if len(encryption_key) != 32:
            raise VaultGuardianError("guardian_encryption_key_invalid")
        self.layout = layout
        self.business_stable_id = self._component(business_stable_id, "business_stable_id")
        self.cipher = AESGCM(bytes(encryption_key))
        self.database = layout.records / "guardian.sqlite3"
        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        self._harden_database_files()
        return connection

    def _harden_database_files(self) -> None:
        """Keep the encrypted database and SQLite sidecars owner-only.

        The payload is encrypted, but metadata and future format changes must not
        depend on the process umask for their confidentiality boundary.
        """
        for path in (
            self.database,
            Path(f"{self.database}-wal"),
            Path(f"{self.database}-shm"),
        ):
            try:
                path.chmod(0o600)
            except FileNotFoundError:
                continue

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS guardian_record_versions (
                    collection TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    version INTEGER NOT NULL CHECK (version > 0),
                    nonce BLOB NOT NULL,
                    ciphertext BLOB NOT NULL,
                    plaintext_sha256 TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    tombstone INTEGER NOT NULL CHECK (tombstone IN (0, 1)),
                    PRIMARY KEY (collection, record_id, version)
                );
                CREATE TABLE IF NOT EXISTS guardian_record_heads (
                    collection TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    PRIMARY KEY (collection, record_id),
                    FOREIGN KEY (collection, record_id, version)
                        REFERENCES guardian_record_versions(collection, record_id, version)
                );
                CREATE TABLE IF NOT EXISTS guardian_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    operation_sha256 TEXT NOT NULL,
                    response_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS guardian_audit_receipts (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    collection TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    plaintext_sha256 TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    previous_receipt_hash TEXT NOT NULL,
                    receipt_hash TEXT NOT NULL UNIQUE
                );
                CREATE TRIGGER IF NOT EXISTS guardian_versions_no_update
                    BEFORE UPDATE ON guardian_record_versions
                    BEGIN SELECT RAISE(ABORT, 'guardian_history_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS guardian_versions_no_delete
                    BEFORE DELETE ON guardian_record_versions
                    BEGIN SELECT RAISE(ABORT, 'guardian_history_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS guardian_idempotency_no_update
                    BEFORE UPDATE ON guardian_idempotency
                    BEGIN SELECT RAISE(ABORT, 'guardian_history_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS guardian_idempotency_no_delete
                    BEFORE DELETE ON guardian_idempotency
                    BEGIN SELECT RAISE(ABORT, 'guardian_history_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS guardian_audit_no_update
                    BEFORE UPDATE ON guardian_audit_receipts
                    BEGIN SELECT RAISE(ABORT, 'guardian_history_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS guardian_audit_no_delete
                    BEFORE DELETE ON guardian_audit_receipts
                    BEGIN SELECT RAISE(ABORT, 'guardian_history_immutable'); END;
                """
            )

    @staticmethod
    def _component(value: str, field: str) -> str:
        result = str(value or "").strip()
        if not SAFE_COMPONENT.fullmatch(result):
            raise VaultGuardianError(f"{field}_invalid")
        return result

    def _aad(self, collection: str, record_id: str, version: int) -> bytes:
        return _canonical(
            {
                "schema_version": GUARDIAN_SCHEMA,
                "business_stable_id": self.business_stable_id,
                "collection": collection,
                "record_id": record_id,
                "version": version,
            }
        )

    def put_record(
        self,
        *,
        collection: str,
        record_id: str,
        payload: Mapping[str, Any],
        expected_version: int | None,
        idempotency_key: str,
        actor_id: str,
        recorded_at: str,
        tombstone: bool = False,
    ) -> dict[str, Any]:
        collection = self._component(collection, "collection")
        record_id = self._component(record_id, "record_id")
        idempotency_key = self._component(idempotency_key, "idempotency_key")
        actor_id = self._component(actor_id, "actor_id")
        raw = _canonical(dict(payload))
        if len(raw) > MAX_RECORD_BYTES:
            raise VaultGuardianError("guardian_record_too_large")
        plaintext_hash = _hash(raw)
        operation = {
            "collection": collection,
            "record_id": record_id,
            "expected_version": expected_version,
            "plaintext_sha256": plaintext_hash,
            "tombstone": bool(tombstone),
            "actor_id": actor_id,
            "recorded_at": recorded_at,
        }
        operation_hash = _hash(operation)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                replay = connection.execute(
                    "SELECT operation_sha256, response_json FROM guardian_idempotency WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if replay:
                    if replay["operation_sha256"] != operation_hash:
                        raise VaultGuardianError("guardian_idempotency_collision")
                    response = json.loads(replay["response_json"])
                    connection.commit()
                    return response
                head = connection.execute(
                    "SELECT version FROM guardian_record_heads WHERE collection = ? AND record_id = ?",
                    (collection, record_id),
                ).fetchone()
                current_version = int(head["version"]) if head else None
                if current_version != expected_version:
                    raise VaultGuardianError("guardian_version_conflict")
                version = (current_version or 0) + 1
                nonce = os.urandom(12)
                ciphertext = self.cipher.encrypt(
                    nonce, raw, self._aad(collection, record_id, version)
                )
                connection.execute(
                    """
                    INSERT INTO guardian_record_versions (
                        collection, record_id, version, nonce, ciphertext,
                        plaintext_sha256, actor_id, recorded_at, tombstone
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        collection, record_id, version, nonce, ciphertext,
                        plaintext_hash, actor_id, recorded_at, int(bool(tombstone)),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO guardian_record_heads (collection, record_id, version)
                    VALUES (?, ?, ?)
                    ON CONFLICT(collection, record_id) DO UPDATE SET version = excluded.version
                    """,
                    (collection, record_id, version),
                )
                previous = connection.execute(
                    "SELECT receipt_hash FROM guardian_audit_receipts ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                receipt = {
                    "schema_version": "tessaris.vault-guardian-receipt.v1",
                    "event": "record_tombstoned" if tombstone else "record_written",
                    "collection": collection,
                    "record_id": record_id,
                    "version": version,
                    "plaintext_sha256": plaintext_hash,
                    "actor_id": actor_id,
                    "recorded_at": recorded_at,
                    "previous_receipt_hash": previous["receipt_hash"] if previous else "genesis",
                }
                receipt_hash = _hash(receipt)
                connection.execute(
                    """
                    INSERT INTO guardian_audit_receipts (
                        event, collection, record_id, version, plaintext_sha256,
                        actor_id, recorded_at, previous_receipt_hash, receipt_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt["event"], collection, record_id, version, plaintext_hash,
                        actor_id, recorded_at, receipt["previous_receipt_hash"], receipt_hash,
                    ),
                )
                response = {
                    "schema_version": GUARDIAN_SCHEMA,
                    "collection": collection,
                    "record_id": record_id,
                    "version": version,
                    "plaintext_sha256": plaintext_hash,
                    "tombstone": bool(tombstone),
                    "receipt_hash": receipt_hash,
                    "idempotent_replay": False,
                }
                connection.execute(
                    "INSERT INTO guardian_idempotency (idempotency_key, operation_sha256, response_json) VALUES (?, ?, ?)",
                    (
                        idempotency_key,
                        operation_hash,
                        json.dumps(response, sort_keys=True, separators=(",", ":")),
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return response

    def get_record(
        self,
        *,
        collection: str,
        record_id: str,
        version: int | None = None,
        include_tombstone: bool = False,
    ) -> dict[str, Any]:
        collection = self._component(collection, "collection")
        record_id = self._component(record_id, "record_id")
        with self._connect() as connection:
            if version is None:
                row = connection.execute(
                    """
                    SELECT v.* FROM guardian_record_versions v
                    JOIN guardian_record_heads h
                      ON h.collection = v.collection AND h.record_id = v.record_id
                     AND h.version = v.version
                    WHERE v.collection = ? AND v.record_id = ?
                    """,
                    (collection, record_id),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM guardian_record_versions WHERE collection = ? AND record_id = ? AND version = ?",
                    (collection, record_id, int(version)),
                ).fetchone()
        if not row:
            raise KeyError("guardian_record_not_found")
        if bool(row["tombstone"]) and not include_tombstone:
            raise KeyError("guardian_record_tombstoned")
        raw = self.cipher.decrypt(
            row["nonce"],
            row["ciphertext"],
            self._aad(collection, record_id, int(row["version"])),
        )
        if _hash(raw) != row["plaintext_sha256"]:
            raise RuntimeError("guardian_record_integrity_failed")
        return {
            "schema_version": GUARDIAN_SCHEMA,
            "collection": collection,
            "record_id": record_id,
            "version": int(row["version"]),
            "payload": json.loads(raw),
            "plaintext_sha256": row["plaintext_sha256"],
            "tombstone": bool(row["tombstone"]),
            "actor_id": row["actor_id"],
            "recorded_at": row["recorded_at"],
        }

    def list_records(self, *, collection: str) -> list[dict[str, Any]]:
        """Return decrypted live heads in deterministic record-id order."""
        collection = self._component(collection, "collection")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT v.record_id FROM guardian_record_versions v
                JOIN guardian_record_heads h
                  ON h.collection = v.collection AND h.record_id = v.record_id
                 AND h.version = v.version
                WHERE v.collection = ? AND v.tombstone = 0
                ORDER BY v.record_id
                """,
                (collection,),
            ).fetchall()
        return [
            self.get_record(collection=collection, record_id=str(row["record_id"]))
            for row in rows
        ]

    def tombstone_record(
        self,
        *,
        collection: str,
        record_id: str,
        expected_version: int,
        reason_code: str,
        idempotency_key: str,
        actor_id: str,
        recorded_at: str,
    ) -> dict[str, Any]:
        reason = self._component(reason_code, "reason_code")
        return self.put_record(
            collection=collection,
            record_id=record_id,
            payload={"tombstone": True, "reason_code": reason},
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            actor_id=actor_id,
            recorded_at=recorded_at,
            tombstone=True,
        )

    def verify_audit_chain(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM guardian_audit_receipts ORDER BY sequence"
            ).fetchall()
        previous = "genesis"
        for row in rows:
            receipt = {
                "schema_version": "tessaris.vault-guardian-receipt.v1",
                "event": row["event"],
                "collection": row["collection"],
                "record_id": row["record_id"],
                "version": int(row["version"]),
                "plaintext_sha256": row["plaintext_sha256"],
                "actor_id": row["actor_id"],
                "recorded_at": row["recorded_at"],
                "previous_receipt_hash": row["previous_receipt_hash"],
            }
            if row["previous_receipt_hash"] != previous or _hash(receipt) != row["receipt_hash"]:
                return {"healthy": False, "receipt_count": len(rows), "failed_sequence": row["sequence"]}
            previous = row["receipt_hash"]
        return {"healthy": True, "receipt_count": len(rows), "head_receipt_hash": previous}
