from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PRICE_BOOK_SCHEMA,
    canonical_hash,
    verify_price_book,
)


PRICE_BOOK_STORE_SCHEMA = "tessaris.photon-price-book-store.v1"
PRICE_BOOK_CANCELLATION_SCHEMA = "tessaris.photon-price-book-cancellation.v1"


def _instant(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("price_book_datetime_invalid") from exc
    if result.tzinfo is None:
        raise ValueError("price_book_datetime_timezone_required")
    return result


class PhotonPriceBookStore:
    """Immutable two-step publication store for founder-authorised Photon pricing."""

    def __init__(self, database_path: str | Path) -> None:
        candidate = Path(database_path).expanduser()
        if candidate.is_symlink():
            raise ValueError("photon_price_book_symlink_database_forbidden")
        self.path = candidate.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS photon_price_books (
                    version TEXT PRIMARY KEY,
                    currency TEXT NOT NULL,
                    region TEXT NOT NULL,
                    cohort TEXT NOT NULL,
                    effective_at TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    published_by TEXT NOT NULL,
                    preview_hash TEXT NOT NULL UNIQUE,
                    signer_public_key TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    customer_content_included INTEGER NOT NULL CHECK (customer_content_included = 0)
                );
                CREATE INDEX IF NOT EXISTS idx_photon_price_effective
                    ON photon_price_books(currency, region, cohort, effective_at);
                CREATE TRIGGER IF NOT EXISTS photon_price_books_no_update
                    BEFORE UPDATE ON photon_price_books
                    BEGIN SELECT RAISE(ABORT, 'photon_price_book_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_price_books_no_delete
                    BEFORE DELETE ON photon_price_books
                    BEGIN SELECT RAISE(ABORT, 'photon_price_book_immutable'); END;
                CREATE TABLE IF NOT EXISTS photon_price_book_cancellations (
                    version TEXT PRIMARY KEY REFERENCES photon_price_books(version),
                    cancelled_at TEXT NOT NULL,
                    cancelled_by TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    customer_content_included INTEGER NOT NULL CHECK (customer_content_included = 0)
                );
                CREATE TRIGGER IF NOT EXISTS photon_price_book_cancellations_no_update
                    BEFORE UPDATE ON photon_price_book_cancellations
                    BEGIN SELECT RAISE(ABORT, 'photon_price_book_cancellation_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_price_book_cancellations_no_delete
                    BEFORE DELETE ON photon_price_book_cancellations
                    BEGIN SELECT RAISE(ABORT, 'photon_price_book_cancellation_immutable'); END;
                """
            )
        os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def publish(
        self,
        envelope: Mapping[str, Any],
        *,
        approved_preview_hash: str,
        actor_id: str,
        published_at: str,
        reauthenticated: bool,
        confirmation: str,
        verifier: Callable[[str, bytes, str], bool] | None = None,
    ) -> dict[str, Any]:
        if not reauthenticated:
            raise PermissionError("photon_price_publish_reauthentication_required")
        if confirmation != "PUBLISH PHOTON PRICE BOOK":
            raise PermissionError("photon_price_publish_confirmation_required")
        actor = str(actor_id or "").strip()
        if not actor or len(actor) > 160:
            raise ValueError("photon_price_publisher_invalid")
        if not verify_price_book(envelope, verifier=verifier):
            raise PermissionError("photon_price_book_signature_invalid")
        payload = dict(envelope["payload"])
        if payload.get("schema_version") != PRICE_BOOK_SCHEMA:
            raise ValueError("photon_price_book_schema_invalid")
        preview_hash = canonical_hash(payload)
        if preview_hash != approved_preview_hash:
            raise PermissionError("photon_price_preview_mismatch")
        effective_at = _instant(payload["effective_at"]).isoformat()
        published_instant = _instant(published_at)
        if _instant(payload["effective_at"]) <= published_instant:
            raise ValueError("photon_price_effective_date_not_future")
        record = {
            "schema_version": PRICE_BOOK_STORE_SCHEMA,
            "version": str(payload["version"]),
            "currency": str(payload["currency"]),
            "region": str(payload["region"]),
            "cohort": str(payload["cohort"]),
            "effective_at": effective_at,
            "published_at": published_instant.isoformat(),
            "published_by": actor,
            "preview_hash": preview_hash,
            "signer_public_key": str(envelope["signer_public_key"]),
            "signature": str(envelope["signature"]),
            "payload": payload,
            "customer_content_included": False,
        }
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO photon_price_books (
                        version, currency, region, cohort, effective_at, published_at,
                        published_by, preview_hash, signer_public_key, signature,
                        payload_json, schema_version, customer_content_included
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        record["version"], record["currency"], record["region"],
                        record["cohort"], record["effective_at"], record["published_at"],
                        record["published_by"], record["preview_hash"],
                        record["signer_public_key"], record["signature"],
                        json.dumps(payload, sort_keys=True, separators=(",", ":")),
                        PRICE_BOOK_STORE_SCHEMA,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = self.get(record["version"])
                if existing != record:
                    raise ValueError("photon_price_book_version_reused") from exc
                return existing
        return record

    def get(self, version: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM photon_price_books WHERE version = ?", (version,)
            ).fetchone()
        if not row:
            raise KeyError("photon_price_book_not_found")
        return self._row(row)

    def applicable(
        self,
        *,
        currency: str,
        region: str,
        cohort: str,
        as_of: str,
    ) -> dict[str, Any]:
        instant = _instant(as_of).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM photon_price_books
                WHERE currency = ? AND region IN (?, 'global') AND cohort IN (?, 'all')
                    AND effective_at <= ?
                    AND NOT EXISTS (
                        SELECT 1 FROM photon_price_book_cancellations cancellations
                        WHERE cancellations.version = photon_price_books.version
                    )
                ORDER BY effective_at DESC, published_at DESC LIMIT 1
                """,
                (currency.upper(), region, cohort, instant),
            ).fetchone()
        if not row:
            raise KeyError("applicable_photon_price_book_not_found")
        return self._row(row)

    def list(self, *, limit: int = 100) -> list[dict[str, Any]]:
        limit = int(limit)
        if not 1 <= limit <= 500:
            raise ValueError("photon_price_book_limit_invalid")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM photon_price_books
                ORDER BY effective_at DESC, published_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row(row) for row in rows]

    def scheduled(
        self,
        *,
        currency: str,
        region: str,
        cohort: str,
        as_of: str,
    ) -> list[dict[str, Any]]:
        instant = _instant(as_of).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM photon_price_books
                WHERE currency = ? AND region IN (?, 'global') AND cohort IN (?, 'all')
                    AND effective_at > ?
                    AND NOT EXISTS (
                        SELECT 1 FROM photon_price_book_cancellations cancellations
                        WHERE cancellations.version = photon_price_books.version
                    )
                ORDER BY effective_at ASC, published_at ASC
                """,
                (currency.upper(), region, cohort, instant),
            ).fetchall()
        return [self._row(row) for row in rows]

    def cancel(
        self,
        version: str,
        *,
        actor_id: str,
        cancelled_at: str,
        reason: str,
        reauthenticated: bool,
        confirmation: str,
    ) -> dict[str, Any]:
        if not reauthenticated:
            raise PermissionError("photon_price_cancel_reauthentication_required")
        if confirmation != "CANCEL PHOTON PRICE BOOK":
            raise PermissionError("photon_price_cancel_confirmation_required")
        actor = str(actor_id or "").strip()
        if not actor or len(actor) > 160:
            raise ValueError("photon_price_canceller_invalid")
        cancellation_reason = str(reason or "").strip()
        if not cancellation_reason or len(cancellation_reason) > 500:
            raise ValueError("photon_price_cancellation_reason_invalid")
        book = self.get(version)
        cancelled_instant = _instant(cancelled_at)
        if _instant(book["effective_at"]) <= cancelled_instant:
            raise ValueError("active_photon_price_book_cannot_be_cancelled")
        record = {
            "schema_version": PRICE_BOOK_CANCELLATION_SCHEMA,
            "version": str(version),
            "cancelled_at": cancelled_instant.isoformat(),
            "cancelled_by": actor,
            "reason": cancellation_reason,
            "customer_content_included": False,
        }
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO photon_price_book_cancellations (
                        version, cancelled_at, cancelled_by, reason,
                        schema_version, customer_content_included
                    ) VALUES (?, ?, ?, ?, ?, 0)
                    """,
                    (
                        record["version"], record["cancelled_at"],
                        record["cancelled_by"], record["reason"],
                        PRICE_BOOK_CANCELLATION_SCHEMA,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                row = connection.execute(
                    "SELECT * FROM photon_price_book_cancellations WHERE version = ?",
                    (version,),
                ).fetchone()
                existing = self._cancellation_row(row) if row else None
                if existing != record:
                    raise ValueError("photon_price_book_cancellation_conflict") from exc
                return existing
        return record

    def cancellation(self, version: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM photon_price_book_cancellations WHERE version = ?",
                (version,),
            ).fetchone()
        if not row:
            raise KeyError("photon_price_book_cancellation_not_found")
        return self._cancellation_row(row)

    def list_cancellations(self, *, limit: int = 100) -> list[dict[str, Any]]:
        limit = int(limit)
        if not 1 <= limit <= 500:
            raise ValueError("photon_price_book_limit_invalid")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM photon_price_book_cancellations
                ORDER BY cancelled_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._cancellation_row(row) for row in rows]

    @staticmethod
    def _cancellation_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "schema_version": row["schema_version"],
            "version": row["version"],
            "cancelled_at": row["cancelled_at"],
            "cancelled_by": row["cancelled_by"],
            "reason": row["reason"],
            "customer_content_included": False,
        }

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["payload_json"])
        if canonical_hash(payload) != row["preview_hash"]:
            raise ValueError("photon_price_book_payload_hash_mismatch")
        stored_identity = {
            "version": row["version"],
            "currency": row["currency"],
            "region": row["region"],
            "cohort": row["cohort"],
        }
        if any(str(payload.get(key)) != value for key, value in stored_identity.items()):
            raise ValueError("photon_price_book_stored_identity_mismatch")
        return {
            "schema_version": row["schema_version"],
            "version": row["version"],
            "currency": row["currency"],
            "region": row["region"],
            "cohort": row["cohort"],
            "effective_at": row["effective_at"],
            "published_at": row["published_at"],
            "published_by": row["published_by"],
            "preview_hash": row["preview_hash"],
            "signer_public_key": row["signer_public_key"],
            "signature": row["signature"],
            "payload": payload,
            "customer_content_included": False,
        }
