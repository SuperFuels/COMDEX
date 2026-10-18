from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonLedgerBackend,
    PhotonLedgerEntry,
    canonical_hash,
)


REVOLUT_FULFILMENT_SCHEMA = "tessaris.photon-revolut-fulfilment.v1"
REVOLUT_REFUND_SCHEMA = "tessaris.photon-revolut-refund.v1"
REVOLUT_DISPUTE_SCHEMA = "tessaris.photon-revolut-dispute.v1"
PHOTON_BILLING_RECORD_SCHEMA = "tessaris.photon-billing-record.v1"
TERMINAL_PAID_STATES = frozenset({"completed"})
TERMINAL_REFUND_STATES = frozenset({"completed"})
ORDER_EVENT_TYPES = frozenset({"ORDER_COMPLETED"})
REFUND_EVENT_TYPES = frozenset({"REFUND_COMPLETED"})
DISPUTE_EVENT_TYPES = frozenset({"DISPUTE_UPDATED"})
MAX_WEBHOOK_BYTES = 1_048_576


class RawWebhookVerifier(Protocol):
    def verify(self, raw_body: bytes, headers: Mapping[str, str]) -> bool: ...


class RevolutOrderReader(Protocol):
    def retrieve_order(self, order_id: str) -> Mapping[str, Any]: ...


class RevolutRefundReader(Protocol):
    def retrieve_refund(self, refund_id: str) -> Mapping[str, Any]: ...


class RevolutDisputeReader(Protocol):
    """Provider adapter returning a normalized authoritative dispute view.

    ``liability_outcome`` is one of pending, merchant_won or merchant_lost.
    Provider-specific state names remain adapter concerns.
    """

    def retrieve_dispute(self, dispute_id: str) -> Mapping[str, Any]: ...


class RevolutHmacWebhookVerifier:
    """Verify Revolut's v1 HMAC over timestamp and untouched raw payload."""

    def __init__(
        self,
        signing_secret: str,
        *,
        tolerance_seconds: int = 300,
        now_milliseconds: Callable[[], int] | None = None,
    ) -> None:
        if not signing_secret:
            raise ValueError("revolut_signing_secret_required")
        self.secret = signing_secret.encode("utf-8")
        self.tolerance_seconds = int(tolerance_seconds)
        self.now_milliseconds = now_milliseconds or (lambda: int(time.time() * 1000))

    @staticmethod
    def _header(headers: Mapping[str, str], name: str) -> str:
        expected = name.lower()
        return next((str(value) for key, value in headers.items() if key.lower() == expected), "")

    def verify(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        timestamp = self._header(headers, "Revolut-Request-Timestamp")
        supplied = self._header(headers, "Revolut-Signature")
        try:
            timestamp_ms = int(timestamp)
            raw_text = raw_body.decode("utf-8")
        except (TypeError, ValueError, UnicodeDecodeError):
            return False
        if abs(int(self.now_milliseconds()) - timestamp_ms) > self.tolerance_seconds * 1000:
            return False
        material = f"v1.{timestamp}.{raw_text}".encode("utf-8")
        expected = "v1=" + hmac.new(self.secret, material, hashlib.sha256).hexdigest()
        candidates = [item.strip() for item in supplied.split(",") if item.strip()]
        return any(hmac.compare_digest(expected, candidate) for candidate in candidates)


class PhotonRevolutFulfilment:
    """State-based exact-once grant boundary for hosted Revolut Merchant checkout."""

    def __init__(self, database_path: str | Path, *, ledger: PhotonLedgerBackend) -> None:
        candidate = Path(database_path).expanduser()
        if candidate.is_symlink():
            raise ValueError("revolut_fulfilment_symlink_database_forbidden")
        self.path = candidate.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self.ledger = ledger
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
                CREATE TABLE IF NOT EXISTS revolut_photon_intents (
                    order_id TEXT PRIMARY KEY,
                    external_reference TEXT NOT NULL UNIQUE,
                    tenant_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    photons INTEGER NOT NULL CHECK (photons > 0),
                    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
                    currency TEXT NOT NULL CHECK (length(currency) = 3),
                    price_book_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    customer_content_included INTEGER NOT NULL CHECK (customer_content_included = 0)
                );
                CREATE TABLE IF NOT EXISTS revolut_photon_fulfilments (
                    order_id TEXT PRIMARY KEY REFERENCES revolut_photon_intents(order_id),
                    provider_event_id TEXT NOT NULL UNIQUE,
                    ledger_transaction_id TEXT NOT NULL UNIQUE,
                    provider_state TEXT NOT NULL,
                    fulfilled_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revolut_photon_refunds (
                    refund_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL REFERENCES revolut_photon_intents(order_id),
                    provider_event_id TEXT NOT NULL UNIQUE,
                    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
                    currency TEXT NOT NULL CHECK (length(currency) = 3),
                    provider_state TEXT NOT NULL,
                    photon_target INTEGER NOT NULL CHECK (photon_target >= 0),
                    observed_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revolut_photon_refund_resolutions (
                    refund_id TEXT PRIMARY KEY REFERENCES revolut_photon_refunds(refund_id),
                    ledger_transaction_id TEXT NOT NULL UNIQUE,
                    photons_reversed INTEGER NOT NULL CHECK (photons_reversed > 0),
                    resolved_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revolut_photon_disputes (
                    dispute_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL REFERENCES revolut_photon_intents(order_id),
                    provider_event_id TEXT NOT NULL UNIQUE,
                    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
                    currency TEXT NOT NULL CHECK (length(currency) = 3),
                    provider_state TEXT NOT NULL,
                    liability_outcome TEXT NOT NULL CHECK (liability_outcome = 'merchant_lost'),
                    photon_target INTEGER NOT NULL CHECK (photon_target >= 0),
                    observed_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revolut_photon_dispute_resolutions (
                    dispute_id TEXT PRIMARY KEY REFERENCES revolut_photon_disputes(dispute_id),
                    ledger_transaction_id TEXT NOT NULL UNIQUE,
                    photons_reversed INTEGER NOT NULL CHECK (photons_reversed > 0),
                    resolved_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS revolut_intents_no_update
                    BEFORE UPDATE ON revolut_photon_intents
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_intents_no_delete
                    BEFORE DELETE ON revolut_photon_intents
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_fulfilments_no_update
                    BEFORE UPDATE ON revolut_photon_fulfilments
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_fulfilments_no_delete
                    BEFORE DELETE ON revolut_photon_fulfilments
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_refunds_no_update
                    BEFORE UPDATE ON revolut_photon_refunds
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_refunds_no_delete
                    BEFORE DELETE ON revolut_photon_refunds
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_refund_resolutions_no_update
                    BEFORE UPDATE ON revolut_photon_refund_resolutions
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_refund_resolutions_no_delete
                    BEFORE DELETE ON revolut_photon_refund_resolutions
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_disputes_no_update
                    BEFORE UPDATE ON revolut_photon_disputes
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_disputes_no_delete
                    BEFORE DELETE ON revolut_photon_disputes
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_dispute_resolutions_no_update
                    BEFORE UPDATE ON revolut_photon_dispute_resolutions
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS revolut_dispute_resolutions_no_delete
                    BEFORE DELETE ON revolut_photon_dispute_resolutions
                    BEGIN SELECT RAISE(ABORT, 'revolut_photon_record_immutable'); END;
                """
            )

    def record_checkout_intent(
        self,
        *,
        order_id: str,
        external_reference: str,
        tenant_id: str,
        product_id: str,
        photons: int,
        amount_minor: int,
        currency: str,
        price_book_version: str,
        created_at: str,
    ) -> dict[str, Any]:
        values = {
            "order_id": self._safe(order_id, "order_id"),
            "external_reference": self._safe(external_reference, "external_reference"),
            "tenant_id": self._safe(tenant_id, "tenant_id"),
            "product_id": self._safe(product_id, "product_id"),
            "photons": int(photons),
            "amount_minor": int(amount_minor),
            "currency": str(currency).strip().upper(),
            "price_book_version": self._safe(price_book_version, "price_book_version"),
            "created_at": str(created_at),
            "customer_content_included": False,
        }
        if values["photons"] <= 0 or values["amount_minor"] <= 0:
            raise ValueError("checkout_value_invalid")
        if len(values["currency"]) != 3 or not values["currency"].isalpha():
            raise ValueError("checkout_currency_invalid")
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO revolut_photon_intents (
                        order_id, external_reference, tenant_id, product_id, photons,
                        amount_minor, currency, price_book_version, created_at,
                        customer_content_included
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        values["order_id"], values["external_reference"], values["tenant_id"],
                        values["product_id"], values["photons"], values["amount_minor"],
                        values["currency"], values["price_book_version"], values["created_at"],
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = self._intent(connection, values["order_id"])
                if existing != values:
                    raise ValueError("checkout_intent_identity_reused") from exc
                return existing
        return values

    def billing_records(
        self, *, tenant_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return immutable, content-free payment evidence for one tenant.

        These records are customer-downloadable evidence derived from verified
        fulfilments.  They deliberately do not claim to be statutory tax
        invoices; that requires the separate tax/numbering policy gate.
        """
        tenant_id = self._safe(tenant_id, "tenant_id")
        limit = int(limit)
        if not 1 <= limit <= 200:
            raise ValueError("photon_billing_record_limit_invalid")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT i.*, f.provider_event_id, f.ledger_transaction_id,
                       f.provider_state, f.fulfilled_at
                FROM revolut_photon_intents i
                JOIN revolut_photon_fulfilments f ON f.order_id = i.order_id
                WHERE i.tenant_id = ?
                ORDER BY f.fulfilled_at DESC, i.order_id DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            ).fetchall()
            records: list[dict[str, Any]] = []
            for row in rows:
                refunds = connection.execute(
                    """
                    SELECT COALESCE(SUM(r.amount_minor), 0) AS refunded_minor,
                           COALESCE(SUM(rr.photons_reversed), 0) AS photons_reversed
                    FROM revolut_photon_refunds r
                    LEFT JOIN revolut_photon_refund_resolutions rr
                      ON rr.refund_id = r.refund_id
                    WHERE r.order_id = ? AND r.provider_state = 'completed'
                    """,
                    (row["order_id"],),
                ).fetchone()
                disputes = connection.execute(
                    """
                    SELECT COALESCE(SUM(d.amount_minor), 0) AS disputed_minor,
                           COALESCE(SUM(dr.photons_reversed), 0) AS photons_reversed,
                           COALESCE(SUM(
                               CASE WHEN d.photon_target > 0 AND dr.dispute_id IS NULL
                                    THEN 1 ELSE 0 END
                           ), 0) AS unresolved_count
                    FROM revolut_photon_disputes d
                    LEFT JOIN revolut_photon_dispute_resolutions dr
                      ON dr.dispute_id = d.dispute_id
                    WHERE d.order_id = ? AND d.liability_outcome = 'merchant_lost'
                    """,
                    (row["order_id"],),
                ).fetchone()
                ledger = self.ledger.transaction(row["ledger_transaction_id"])
                payload = {
                    "schema_version": PHOTON_BILLING_RECORD_SCHEMA,
                    "document_kind": "photon_bundle_payment_receipt",
                    "tax_invoice": False,
                    "receipt_id": f"revolut:{row['order_id']}",
                    "order_id": row["order_id"],
                    "external_reference": row["external_reference"],
                    "product_id": row["product_id"],
                    "amount_minor": int(row["amount_minor"]),
                    "refunded_minor": int(refunds["refunded_minor"]),
                    "disputed_minor": int(disputes["disputed_minor"]),
                    "currency": row["currency"],
                    "photons_granted": int(row["photons"]),
                    "photons_reversed": int(refunds["photons_reversed"]),
                    "photons_dispute_reversed": int(disputes["photons_reversed"]),
                    "commercial_hold": int(disputes["unresolved_count"]) > 0,
                    "price_book_version": row["price_book_version"],
                    "provider": "revolut",
                    "provider_state": row["provider_state"],
                    "paid_at": row["fulfilled_at"],
                    "ledger_transaction_id": row["ledger_transaction_id"],
                    "ledger_transaction_hash": ledger["transaction_hash"],
                    "customer_content_included": False,
                    "local_model_tokens_billed": False,
                }
                records.append({**payload, "record_hash": canonical_hash(payload)})
        return records

    def handle_webhook(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        *,
        verifier: RawWebhookVerifier,
        orders: RevolutOrderReader,
    ) -> dict[str, Any]:
        self._validate_webhook_size(raw_body)
        if not verifier.verify(raw_body, headers):
            raise PermissionError("revolut_webhook_signature_invalid")
        try:
            event = json.loads(raw_body.decode("utf-8"))
            event_type = self._safe(str(event["event"]), "event_type")
            order_id = self._safe(str(event["order_id"]), "order_id")
            event_id = "event:" + hashlib.sha256(raw_body).hexdigest()
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("revolut_webhook_payload_invalid") from exc
        if event_type not in ORDER_EVENT_TYPES:
            raise ValueError("revolut_order_event_type_invalid")

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM revolut_photon_fulfilments WHERE provider_event_id = ? OR order_id = ?",
                (event_id, order_id),
            ).fetchone()
            if existing:
                if existing["provider_event_id"] == event_id and existing["order_id"] != order_id:
                    raise ValueError("revolut_event_identity_reused")
                fulfilled_intent = self._intent(connection, existing["order_id"])
                return self._fulfilment(
                    existing, replay=True, photons=int(fulfilled_intent["photons"])
                )
            intent = self._intent(connection, order_id)

        authoritative = dict(orders.retrieve_order(order_id))
        self._validate_authoritative_order(authoritative, intent)
        provider_state = str(authoritative.get("state") or "").strip().lower()
        if provider_state not in TERMINAL_PAID_STATES:
            return {
                "schema_version": REVOLUT_FULFILMENT_SCHEMA,
                "order_id": order_id,
                "provider_event_id": event_id,
                "provider_state": provider_state or "unknown",
                "status": "awaiting_terminal_paid_state",
                "photons_granted": 0,
                "customer_content_included": False,
            }

        transaction_id = f"revolut-grant:{order_id}"
        self.ledger.post(
            transaction_id=transaction_id,
            tenant_id=intent["tenant_id"],
            reason="revolut_paid_photon_grant",
            source_receipt_id=f"revolut:{order_id}",
            rate_card_version=intent["price_book_version"],
            idempotency_key=f"revolut-order:{order_id}",
            recorded_at=str(authoritative.get("updated_at") or intent["created_at"]),
            entries=[
                PhotonLedgerEntry("platform.grant-liability", -int(intent["photons"])),
                PhotonLedgerEntry("customer.available", int(intent["photons"])),
            ],
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            was_existing = False
            try:
                existing = connection.execute(
                    "SELECT * FROM revolut_photon_fulfilments WHERE order_id = ?",
                    (order_id,),
                ).fetchone()
                if existing:
                    was_existing = True
                else:
                    connection.execute(
                        """
                        INSERT INTO revolut_photon_fulfilments (
                            order_id, provider_event_id, ledger_transaction_id,
                            provider_state, fulfilled_at, schema_version
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            order_id, event_id, transaction_id, provider_state,
                            str(authoritative.get("updated_at") or intent["created_at"]),
                            REVOLUT_FULFILMENT_SCHEMA,
                        ),
                    )
                    existing = connection.execute(
                        "SELECT * FROM revolut_photon_fulfilments WHERE order_id = ?",
                        (order_id,),
                    ).fetchone()
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return self._fulfilment(
            existing,
            replay=was_existing,
            photons=int(intent["photons"]),
        )

    def handle_refund_webhook(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        *,
        verifier: RawWebhookVerifier,
        refunds: RevolutRefundReader,
    ) -> dict[str, Any]:
        """Observe an authoritative completed refund and reverse its Photon grant exactly once."""
        self._validate_webhook_size(raw_body)
        if not verifier.verify(raw_body, headers):
            raise PermissionError("revolut_webhook_signature_invalid")
        try:
            event = json.loads(raw_body.decode("utf-8"))
            event_type = self._safe(str(event["event"]), "event_type")
            order_id = self._safe(str(event["order_id"]), "order_id")
            refund_id = self._safe(str(event["refund_id"]), "refund_id")
            event_id = "event:" + hashlib.sha256(raw_body).hexdigest()
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("revolut_refund_webhook_payload_invalid") from exc
        if event_type not in REFUND_EVENT_TYPES:
            raise ValueError("revolut_refund_event_type_invalid")

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM revolut_photon_refunds WHERE refund_id = ? OR provider_event_id = ?",
                (refund_id, event_id),
            ).fetchone()
            if existing:
                if existing["refund_id"] != refund_id or existing["order_id"] != order_id:
                    raise ValueError("revolut_refund_identity_reused")
                return self.resolve_refund(refund_id, recorded_at=existing["observed_at"])
            intent = self._intent(connection, order_id)
            fulfilled = connection.execute(
                "SELECT 1 FROM revolut_photon_fulfilments WHERE order_id = ?", (order_id,)
            ).fetchone()
            if not fulfilled:
                raise ValueError("revolut_refund_unfulfilled_order")

        authoritative = dict(refunds.retrieve_refund(refund_id))
        amount_minor = int(authoritative.get("amount_minor") or 0)
        currency = str(authoritative.get("currency") or "").strip().upper()
        provider_state = str(authoritative.get("state") or "").strip().lower()
        comparisons = {
            "refund_id": str(authoritative.get("id") or "") == refund_id,
            "order_id": str(authoritative.get("order_id") or "") == order_id,
            "currency": currency == intent["currency"],
        }
        failed = sorted(key for key, matches in comparisons.items() if not matches)
        if failed:
            raise PermissionError(f"revolut_refund_mismatch:{','.join(failed)}")
        if amount_minor <= 0:
            raise ValueError("revolut_refund_amount_invalid")
        if provider_state not in TERMINAL_REFUND_STATES:
            return {
                "schema_version": REVOLUT_REFUND_SCHEMA, "refund_id": refund_id,
                "order_id": order_id, "provider_state": provider_state or "unknown",
                "status": "awaiting_terminal_refund_state", "photons_reversed": 0,
                "customer_content_included": False,
            }

        observed_at = str(authoritative.get("updated_at") or intent["created_at"])
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                """
                SELECT
                  (SELECT COALESCE(SUM(amount_minor), 0)
                     FROM revolut_photon_refunds WHERE order_id = ?)
                  +
                  (SELECT COALESCE(SUM(amount_minor), 0)
                     FROM revolut_photon_disputes WHERE order_id = ?),
                  (SELECT COALESCE(SUM(photon_target), 0)
                     FROM revolut_photon_refunds WHERE order_id = ?)
                  +
                  (SELECT COALESCE(SUM(photon_target), 0)
                     FROM revolut_photon_disputes WHERE order_id = ?)
                """,
                (order_id, order_id, order_id, order_id),
            ).fetchone()
            cumulative_amount = int(prior[0]) + amount_minor
            if cumulative_amount > int(intent["amount_minor"]):
                connection.rollback()
                raise ValueError("revolut_refund_exceeds_order")
            cumulative_target = (
                int(intent["photons"])
                if cumulative_amount == int(intent["amount_minor"])
                else cumulative_amount * int(intent["photons"]) // int(intent["amount_minor"])
            )
            photon_target = cumulative_target - int(prior[1])
            connection.execute(
                """
                INSERT INTO revolut_photon_refunds (
                    refund_id, order_id, provider_event_id, amount_minor, currency,
                    provider_state, photon_target, observed_at, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    refund_id, order_id, event_id, amount_minor, currency,
                    provider_state, photon_target, observed_at, REVOLUT_REFUND_SCHEMA,
                ),
            )
            connection.commit()
        return self.resolve_refund(refund_id, recorded_at=observed_at)

    def resolve_refund(self, refund_id: str, *, recorded_at: str) -> dict[str, Any]:
        """Retry a pending refund reversal after sufficient unspent Photons are available."""
        refund_id = self._safe(refund_id, "refund_id")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT r.*, i.tenant_id, i.price_book_version
                FROM revolut_photon_refunds r
                JOIN revolut_photon_intents i ON i.order_id = r.order_id
                WHERE r.refund_id = ?
                """,
                (refund_id,),
            ).fetchone()
            if not row:
                raise KeyError("revolut_refund_not_found")
            resolution = connection.execute(
                "SELECT * FROM revolut_photon_refund_resolutions WHERE refund_id = ?",
                (refund_id,),
            ).fetchone()
        if resolution:
            return self._refund_result(row, resolution=resolution, replay=True)
        photons = int(row["photon_target"])
        if photons == 0:
            return self._refund_result(row, resolution=None, replay=False)
        transaction_id = f"revolut-refund:{refund_id}"
        try:
            self.ledger.post(
                transaction_id=transaction_id,
                tenant_id=row["tenant_id"],
                reason="revolut_refund_photon_reversal",
                source_receipt_id=f"revolut-refund:{refund_id}",
                rate_card_version=row["price_book_version"],
                idempotency_key=f"revolut-refund:{refund_id}",
                recorded_at=recorded_at,
                entries=[
                    PhotonLedgerEntry("customer.available", -photons),
                    PhotonLedgerEntry("platform.grant-liability", photons),
                ],
                nonnegative_accounts=["customer.available"],
            )
        except ValueError as exc:
            if str(exc) != "ledger_protected_account_insufficient":
                raise
            return self._refund_result(row, resolution=None, replay=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO revolut_photon_refund_resolutions (
                    refund_id, ledger_transaction_id, photons_reversed, resolved_at
                ) VALUES (?, ?, ?, ?)
                """,
                (refund_id, transaction_id, photons, recorded_at),
            )
            resolution = connection.execute(
                "SELECT * FROM revolut_photon_refund_resolutions WHERE refund_id = ?",
                (refund_id,),
            ).fetchone()
        return self._refund_result(row, resolution=resolution, replay=False)

    def handle_dispute_webhook(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        *,
        verifier: RawWebhookVerifier,
        disputes: RevolutDisputeReader,
    ) -> dict[str, Any]:
        """Observe an authoritative normalized dispute and reverse final loss once."""
        self._validate_webhook_size(raw_body)
        if not verifier.verify(raw_body, headers):
            raise PermissionError("revolut_webhook_signature_invalid")
        try:
            event = json.loads(raw_body.decode("utf-8"))
            event_type = self._safe(str(event["event"]), "event_type")
            order_id = self._safe(str(event["order_id"]), "order_id")
            dispute_id = self._safe(str(event["dispute_id"]), "dispute_id")
            event_id = "event:" + hashlib.sha256(raw_body).hexdigest()
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("revolut_dispute_webhook_payload_invalid") from exc
        if event_type not in DISPUTE_EVENT_TYPES:
            raise ValueError("revolut_dispute_event_type_invalid")

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM revolut_photon_disputes WHERE dispute_id = ? OR provider_event_id = ?",
                (dispute_id, event_id),
            ).fetchone()
            if existing:
                if existing["dispute_id"] != dispute_id or existing["order_id"] != order_id:
                    raise ValueError("revolut_dispute_identity_reused")
                return self.resolve_dispute(
                    dispute_id, recorded_at=existing["observed_at"]
                )
            intent = self._intent(connection, order_id)
            fulfilled = connection.execute(
                "SELECT 1 FROM revolut_photon_fulfilments WHERE order_id = ?", (order_id,)
            ).fetchone()
            if not fulfilled:
                raise ValueError("revolut_dispute_unfulfilled_order")

        authoritative = dict(disputes.retrieve_dispute(dispute_id))
        amount_minor = int(authoritative.get("amount_minor") or 0)
        currency = str(authoritative.get("currency") or "").strip().upper()
        provider_state = str(authoritative.get("state") or "").strip().lower()
        liability_outcome = str(
            authoritative.get("liability_outcome") or ""
        ).strip().lower()
        comparisons = {
            "dispute_id": str(authoritative.get("id") or "") == dispute_id,
            "order_id": str(authoritative.get("order_id") or "") == order_id,
            "currency": currency == intent["currency"],
        }
        failed = sorted(key for key, matches in comparisons.items() if not matches)
        if failed:
            raise PermissionError(f"revolut_dispute_mismatch:{','.join(failed)}")
        if amount_minor <= 0:
            raise ValueError("revolut_dispute_amount_invalid")
        if liability_outcome not in {"pending", "merchant_won", "merchant_lost"}:
            raise ValueError("revolut_dispute_outcome_invalid")
        if liability_outcome != "merchant_lost":
            return {
                "schema_version": REVOLUT_DISPUTE_SCHEMA,
                "dispute_id": dispute_id,
                "order_id": order_id,
                "provider_state": provider_state or "unknown",
                "liability_outcome": liability_outcome,
                "status": (
                    "awaiting_terminal_dispute_state"
                    if liability_outcome == "pending"
                    else "closed_no_debit"
                ),
                "photons_reversed": 0,
                "commercial_hold": False,
                "customer_content_included": False,
            }

        observed_at = str(authoritative.get("updated_at") or intent["created_at"])
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                """
                SELECT
                  (SELECT COALESCE(SUM(amount_minor), 0)
                     FROM revolut_photon_refunds WHERE order_id = ?)
                  +
                  (SELECT COALESCE(SUM(amount_minor), 0)
                     FROM revolut_photon_disputes WHERE order_id = ?),
                  (SELECT COALESCE(SUM(photon_target), 0)
                     FROM revolut_photon_refunds WHERE order_id = ?)
                  +
                  (SELECT COALESCE(SUM(photon_target), 0)
                     FROM revolut_photon_disputes WHERE order_id = ?)
                """,
                (order_id, order_id, order_id, order_id),
            ).fetchone()
            cumulative_amount = int(prior[0]) + amount_minor
            if cumulative_amount > int(intent["amount_minor"]):
                connection.rollback()
                raise ValueError("revolut_dispute_exceeds_order")
            cumulative_target = (
                int(intent["photons"])
                if cumulative_amount == int(intent["amount_minor"])
                else cumulative_amount * int(intent["photons"])
                // int(intent["amount_minor"])
            )
            photon_target = cumulative_target - int(prior[1])
            connection.execute(
                """
                INSERT INTO revolut_photon_disputes (
                    dispute_id, order_id, provider_event_id, amount_minor, currency,
                    provider_state, liability_outcome, photon_target, observed_at,
                    schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dispute_id, order_id, event_id, amount_minor, currency,
                    provider_state, liability_outcome, photon_target, observed_at,
                    REVOLUT_DISPUTE_SCHEMA,
                ),
            )
            connection.commit()
        return self.resolve_dispute(dispute_id, recorded_at=observed_at)

    def resolve_dispute(self, dispute_id: str, *, recorded_at: str) -> dict[str, Any]:
        """Retry a final-loss reversal after an approved balance recovery."""
        dispute_id = self._safe(dispute_id, "dispute_id")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT d.*, i.tenant_id, i.price_book_version
                FROM revolut_photon_disputes d
                JOIN revolut_photon_intents i ON i.order_id = d.order_id
                WHERE d.dispute_id = ?
                """,
                (dispute_id,),
            ).fetchone()
            if not row:
                raise KeyError("revolut_dispute_not_found")
            resolution = connection.execute(
                "SELECT * FROM revolut_photon_dispute_resolutions WHERE dispute_id = ?",
                (dispute_id,),
            ).fetchone()
        if resolution:
            return self._dispute_result(row, resolution=resolution, replay=True)
        photons = int(row["photon_target"])
        if photons == 0:
            return self._dispute_result(row, resolution=None, replay=False)
        transaction_id = f"revolut-dispute:{dispute_id}"
        try:
            self.ledger.post(
                transaction_id=transaction_id,
                tenant_id=row["tenant_id"],
                reason="revolut_dispute_photon_reversal",
                source_receipt_id=f"revolut-dispute:{dispute_id}",
                rate_card_version=row["price_book_version"],
                idempotency_key=f"revolut-dispute:{dispute_id}",
                recorded_at=recorded_at,
                entries=[
                    PhotonLedgerEntry("customer.available", -photons),
                    PhotonLedgerEntry("platform.grant-liability", photons),
                ],
                nonnegative_accounts=["customer.available"],
            )
        except ValueError as exc:
            if str(exc) != "ledger_protected_account_insufficient":
                raise
            return self._dispute_result(row, resolution=None, replay=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO revolut_photon_dispute_resolutions (
                    dispute_id, ledger_transaction_id, photons_reversed, resolved_at
                ) VALUES (?, ?, ?, ?)
                """,
                (dispute_id, transaction_id, photons, recorded_at),
            )
            resolution = connection.execute(
                "SELECT * FROM revolut_photon_dispute_resolutions WHERE dispute_id = ?",
                (dispute_id,),
            ).fetchone()
        return self._dispute_result(row, resolution=resolution, replay=False)

    def commercial_status(self, *, tenant_id: str) -> dict[str, Any]:
        tenant_id = self._safe(tenant_id, "tenant_id")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS unresolved_count,
                       COALESCE(SUM(d.amount_minor), 0) AS disputed_minor,
                       COALESCE(SUM(d.photon_target), 0) AS photons_pending_reversal
                FROM revolut_photon_disputes d
                JOIN revolut_photon_intents i ON i.order_id = d.order_id
                LEFT JOIN revolut_photon_dispute_resolutions dr
                  ON dr.dispute_id = d.dispute_id
                WHERE i.tenant_id = ? AND d.photon_target > 0
                  AND dr.dispute_id IS NULL
                """,
                (tenant_id,),
            ).fetchone()
        unresolved = int(row["unresolved_count"])
        return {
            "tenant_id": tenant_id,
            "commercial_hold": unresolved > 0,
            "unresolved_dispute_count": unresolved,
            "disputed_minor": int(row["disputed_minor"]),
            "photons_pending_reversal": int(row["photons_pending_reversal"]),
            "customer_content_included": False,
        }

    @staticmethod
    def _safe(value: str, field: str) -> str:
        result = str(value or "").strip()
        if not result or len(result) > 160 or any(char.isspace() for char in result):
            raise ValueError(f"{field}_invalid")
        return result

    @staticmethod
    def _validate_webhook_size(raw_body: bytes) -> None:
        if not isinstance(raw_body, bytes) or not 1 <= len(raw_body) <= MAX_WEBHOOK_BYTES:
            raise ValueError("revolut_webhook_size_invalid")

    @staticmethod
    def _intent(connection: sqlite3.Connection, order_id: str) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM revolut_photon_intents WHERE order_id = ?", (order_id,)
        ).fetchone()
        if not row:
            raise KeyError("revolut_checkout_intent_not_found")
        return {
            "order_id": row["order_id"],
            "external_reference": row["external_reference"],
            "tenant_id": row["tenant_id"],
            "product_id": row["product_id"],
            "photons": int(row["photons"]),
            "amount_minor": int(row["amount_minor"]),
            "currency": row["currency"],
            "price_book_version": row["price_book_version"],
            "created_at": row["created_at"],
            "customer_content_included": False,
        }

    @staticmethod
    def _validate_authoritative_order(order: Mapping[str, Any], intent: Mapping[str, Any]) -> None:
        comparisons = {
            "order_id": str(order.get("id") or "") == intent["order_id"],
            "external_reference": str(order.get("external_reference") or "")
            == intent["external_reference"],
            "amount_minor": int(order.get("amount_minor") or -1) == intent["amount_minor"],
            "currency": str(order.get("currency") or "").upper() == intent["currency"],
        }
        failed = sorted(key for key, matches in comparisons.items() if not matches)
        if failed:
            raise PermissionError(f"revolut_order_mismatch:{','.join(failed)}")

    @staticmethod
    def _fulfilment(
        row: sqlite3.Row,
        *,
        replay: bool,
        photons: int | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": row["schema_version"],
            "order_id": row["order_id"],
            "provider_event_id": row["provider_event_id"],
            "provider_state": row["provider_state"],
            "ledger_transaction_id": row["ledger_transaction_id"],
            "fulfilled_at": row["fulfilled_at"],
            "status": "fulfilled",
            "photons_granted": photons,
            "replay": replay,
            "customer_content_included": False,
        }

    @staticmethod
    def _refund_result(
        row: sqlite3.Row, *, resolution: sqlite3.Row | None, replay: bool
    ) -> dict[str, Any]:
        target = int(row["photon_target"])
        if resolution:
            status = "reversed"
            reversed_photons = int(resolution["photons_reversed"])
            transaction_id = resolution["ledger_transaction_id"]
        elif target == 0:
            status = "recorded_no_photon_delta"
            reversed_photons = 0
            transaction_id = None
        else:
            status = "manual_review_required"
            reversed_photons = 0
            transaction_id = None
        return {
            "schema_version": row["schema_version"],
            "refund_id": row["refund_id"], "order_id": row["order_id"],
            "provider_event_id": row["provider_event_id"],
            "provider_state": row["provider_state"],
            "amount_minor": int(row["amount_minor"]), "currency": row["currency"],
            "photon_target": target, "photons_reversed": reversed_photons,
            "ledger_transaction_id": transaction_id, "status": status,
            "replay": replay, "customer_content_included": False,
        }

    @staticmethod
    def _dispute_result(
        row: sqlite3.Row, *, resolution: sqlite3.Row | None, replay: bool
    ) -> dict[str, Any]:
        target = int(row["photon_target"])
        if resolution:
            status = "reversed"
            reversed_photons = int(resolution["photons_reversed"])
            transaction_id = resolution["ledger_transaction_id"]
            hold = False
        elif target == 0:
            status = "recorded_no_photon_delta"
            reversed_photons = 0
            transaction_id = None
            hold = False
        else:
            status = "manual_review_required"
            reversed_photons = 0
            transaction_id = None
            hold = True
        return {
            "schema_version": row["schema_version"],
            "dispute_id": row["dispute_id"],
            "order_id": row["order_id"],
            "provider_event_id": row["provider_event_id"],
            "provider_state": row["provider_state"],
            "liability_outcome": row["liability_outcome"],
            "amount_minor": int(row["amount_minor"]),
            "currency": row["currency"],
            "photon_target": target,
            "photons_reversed": reversed_photons,
            "ledger_transaction_id": transaction_id,
            "status": status,
            "commercial_hold": hold,
            "replay": replay,
            "customer_content_included": False,
        }
