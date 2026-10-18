from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Iterable, Mapping, Protocol

PHOTON_ASSET_NAMESPACE = "TESSARIS_PHOTON_CREDIT_V1"
PRICE_BOOK_SCHEMA = "tessaris.photon-price-book.v1"
LEDGER_TRANSACTION_SCHEMA = "tessaris.photon-ledger-transaction.v1"
WORK_RECEIPT_SCHEMA = "tessaris.photon-work-receipt.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
CONTENT_KEYS = re.compile(
    r"prompt|response|result|message|document|customer.?content|conversation|secret|password|private.?key|file.?path",
    re.IGNORECASE,
)


class PriceBookSigner(Protocol):
    public_key_b64: str

    def sign(self, payload: bytes) -> str: ...


class PhotonLedgerBackend(Protocol):
    def post(self, **kwargs: Any) -> dict[str, Any]: ...

    def balances(self, *, tenant_id: str) -> dict[str, int]: ...


class PhotonWorkReceiptSink(Protocol):
    def enqueue(
        self, receipt: Mapping[str, Any], *, event_id: str, recorded_at: str
    ) -> dict[str, Any]: ...


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _identifier(value: str, field: str) -> str:
    result = str(value or "").strip()
    if not SAFE_ID.fullmatch(result):
        raise ValueError(f"{field}_invalid")
    return result


@dataclass(frozen=True)
class PhotonPriceBook:
    version: str
    currency: str
    minor_units_per_1000_photons: int
    action_rates: Mapping[str, int]
    effective_at: str
    region: str
    cohort: str
    reason: str

    def payload(self) -> dict[str, Any]:
        _identifier(self.version, "price_book_version")
        currency = self.currency.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("price_book_currency_invalid")
        if not 1 <= int(self.minor_units_per_1000_photons) <= 1_000_000_000:
            raise ValueError("photon_price_out_of_range")
        if not self.action_rates:
            raise ValueError("action_rates_missing")
        rates: dict[str, int] = {}
        for action_type, photons in sorted(self.action_rates.items()):
            action = _identifier(action_type, "action_type")
            quantity = int(photons)
            if not 1 <= quantity <= 1_000_000:
                raise ValueError("action_rate_out_of_range")
            rates[action] = quantity
        if not self.effective_at or not self.reason.strip():
            raise ValueError("price_book_governance_fields_missing")
        return {
            "schema_version": PRICE_BOOK_SCHEMA,
            "asset_namespace": PHOTON_ASSET_NAMESPACE,
            "version": self.version,
            "currency": currency,
            "minor_units_per_1000_photons": int(self.minor_units_per_1000_photons),
            "action_rates": rates,
            "effective_at": self.effective_at,
            "region": self.region.strip() or "global",
            "cohort": self.cohort.strip() or "all",
            "reason": self.reason.strip(),
            "local_model_tokens_billed": False,
            "local_compute_billed": False,
            "retroactive": False,
        }

    def minor_units_for(self, photons: int) -> int:
        if int(photons) < 0:
            raise ValueError("photon_quantity_invalid")
        exact = Decimal(int(photons)) * Decimal(int(self.minor_units_per_1000_photons)) / Decimal(1000)
        return int(exact.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def preview(self) -> dict[str, Any]:
        payload = self.payload()
        return {
            "schema_version": "tessaris.photon-price-preview.v1",
            "price_book_hash": canonical_hash(payload),
            "currency": payload["currency"],
            "minor_units_per_1000_photons": payload["minor_units_per_1000_photons"],
            "outcomes": [
                {
                    "action_type": action,
                    "photons": photons,
                    "approximate_minor_units": self.minor_units_for(photons),
                }
                for action, photons in payload["action_rates"].items()
            ],
            "published": False,
        }


def sign_price_book(book: PhotonPriceBook, signer: PriceBookSigner) -> dict[str, Any]:
    payload = book.payload()
    return {
        "payload": payload,
        "signer_public_key": signer.public_key_b64,
        "signature": signer.sign(canonical_bytes(payload)),
    }


def verify_price_book(
    envelope: Mapping[str, Any],
    *,
    verifier: Callable[[str, bytes, str], bool] | None = None,
) -> bool:
    try:
        payload = dict(envelope["payload"])
        if payload.get("schema_version") != PRICE_BOOK_SCHEMA:
            return False
        if verifier is None:
            from backend.modules.aion_fabric.identity import DeviceIdentity

            verifier = DeviceIdentity.verify
        return verifier(
            str(envelope["signer_public_key"]),
            canonical_bytes(payload),
            str(envelope["signature"]),
        )
    except (KeyError, TypeError, ValueError):
        return False


@dataclass(frozen=True)
class PhotonLedgerEntry:
    account: str
    quantity_photons: int

    def payload(self) -> dict[str, Any]:
        return {
            "account": _identifier(self.account, "ledger_account"),
            "quantity_photons": int(self.quantity_photons),
        }


class PhotonLedger:
    """Content-free double-entry reducer; durable storage is a separate control-plane adapter."""

    def __init__(self) -> None:
        self._transactions: list[dict[str, Any]] = []
        self._idempotency: dict[str, dict[str, Any]] = {}

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
    ) -> dict[str, Any]:
        transaction_id = _identifier(transaction_id, "transaction_id")
        tenant_id = _identifier(tenant_id, "tenant_id")
        source_receipt_id = _identifier(source_receipt_id, "source_receipt_id")
        rate_card_version = _identifier(rate_card_version, "rate_card_version")
        idempotency_key = _identifier(idempotency_key, "idempotency_key")
        if CONTENT_KEYS.search(reason):
            raise ValueError("ledger_reason_contains_content_key")
        reason = _identifier(reason, "ledger_reason")
        rows = [entry.payload() for entry in entries]
        if len(rows) < 2 or any(row["quantity_photons"] == 0 for row in rows):
            raise ValueError("ledger_entries_invalid")
        if sum(row["quantity_photons"] for row in rows) != 0:
            raise ValueError("ledger_transaction_unbalanced")
        unsigned = {
            "schema_version": LEDGER_TRANSACTION_SCHEMA,
            "asset_namespace": PHOTON_ASSET_NAMESPACE,
            "transaction_id": transaction_id,
            "tenant_id": tenant_id,
            "reason": reason,
            "source_receipt_id": source_receipt_id,
            "rate_card_version": rate_card_version,
            "idempotency_key": idempotency_key,
            "recorded_at": recorded_at,
            "entries": rows,
            "customer_content_included": False,
        }
        transaction = {**unsigned, "transaction_hash": canonical_hash(unsigned)}
        prior = self._idempotency.get(idempotency_key)
        if prior:
            if prior["transaction_hash"] != transaction["transaction_hash"]:
                raise ValueError("ledger_idempotency_collision")
            return copy.deepcopy(prior)
        if any(item["transaction_id"] == transaction_id for item in self._transactions):
            raise ValueError("ledger_transaction_id_reused")
        self._transactions.append(transaction)
        self._idempotency[idempotency_key] = transaction
        return copy.deepcopy(transaction)

    def balances(self, *, tenant_id: str | None = None) -> dict[str, int]:
        result: dict[str, int] = {}
        for transaction in self._transactions:
            if tenant_id is not None and transaction["tenant_id"] != tenant_id:
                continue
            for entry in transaction["entries"]:
                result[entry["account"]] = result.get(entry["account"], 0) + int(
                    entry["quantity_photons"]
                )
        return dict(sorted(result.items()))

    def export(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._transactions)


class PhotonWalletEngine:
    """In-memory lifecycle proof for reserve, capture and release semantics."""

    def __init__(
        self,
        ledger: PhotonLedgerBackend,
        *,
        tenant_id: str,
        price_book: PhotonPriceBook,
        receipt_sink: PhotonWorkReceiptSink | None = None,
    ) -> None:
        self.ledger = ledger
        self.tenant_id = _identifier(tenant_id, "tenant_id")
        self.price_book = price_book
        self.receipt_sink = receipt_sink
        self._reservations: dict[str, dict[str, Any]] = {}
        self._last_receipt_hash = "genesis"

    def available(self) -> int:
        return self.ledger.balances(tenant_id=self.tenant_id).get("customer.available", 0)

    def reserve(
        self,
        *,
        reservation_id: str,
        action_type: str,
        created_at: str,
        billing_parent_id: str | None = None,
        included_in_parent: bool = False,
    ) -> dict[str, Any]:
        reservation_id = _identifier(reservation_id, "reservation_id")
        action_type = _identifier(action_type, "action_type")
        prior = self._reservations.get(reservation_id)
        if prior:
            expected = (action_type, billing_parent_id, bool(included_in_parent))
            actual = (prior["action_type"], prior["billing_parent_id"], prior["included_in_parent"])
            if expected != actual:
                raise ValueError("reservation_id_reused")
            return copy.deepcopy(prior)
        if included_in_parent and not billing_parent_id:
            raise ValueError("billing_parent_required")
        rates = self.price_book.payload()["action_rates"]
        if action_type not in rates:
            raise KeyError("action_rate_not_found")
        photons = 0 if included_in_parent else int(rates[action_type])
        if photons > self.available():
            raise ValueError("photon_balance_insufficient")
        if photons:
            self.ledger.post(
                transaction_id=f"reservation:{reservation_id}",
                tenant_id=self.tenant_id,
                reason="outcome_reservation",
                source_receipt_id=reservation_id,
                rate_card_version=self.price_book.version,
                idempotency_key=f"reservation:{reservation_id}",
                recorded_at=created_at,
                entries=[
                    PhotonLedgerEntry("customer.available", -photons),
                    PhotonLedgerEntry("customer.reserved", photons),
                ],
            )
        record = {
            "schema_version": "tessaris.photon-reservation.v1",
            "reservation_id": reservation_id,
            "tenant_id": self.tenant_id,
            "action_type": action_type,
            "photons": photons,
            "rate_card_version": self.price_book.version,
            "billing_parent_id": _identifier(billing_parent_id, "billing_parent_id") if billing_parent_id else None,
            "included_in_parent": bool(included_in_parent),
            "state": "included" if included_in_parent else "reserved",
            "created_at": created_at,
            "customer_content_included": False,
        }
        self._reservations[reservation_id] = record
        return copy.deepcopy(record)

    def capture(
        self,
        *,
        reservation_id: str,
        outcome_id: str,
        device_id: str,
        tenant_commitment: str,
        success_evidence_code: str,
        completed_at: str,
    ) -> dict[str, Any]:
        reservation = self._reservation(reservation_id)
        if reservation["state"] in {"captured", "included"}:
            return copy.deepcopy(reservation)
        if reservation["state"] != "reserved":
            raise ValueError("reservation_not_capturable")
        photons = int(reservation["photons"])
        self.ledger.post(
            transaction_id=f"capture:{reservation_id}",
            tenant_id=self.tenant_id,
            reason="verified_outcome_capture",
            source_receipt_id=f"work:{reservation_id}",
            rate_card_version=self.price_book.version,
            idempotency_key=f"capture:{reservation_id}",
            recorded_at=completed_at,
            entries=[
                PhotonLedgerEntry("customer.reserved", -photons),
                PhotonLedgerEntry("platform.consumed", photons),
            ],
        )
        receipt = build_work_receipt(
            receipt_id=f"work:{reservation_id}",
            tenant_commitment=tenant_commitment,
            device_id=device_id,
            action_type=reservation["action_type"],
            outcome_id=outcome_id,
            photons=photons,
            rate_card_version=self.price_book.version,
            reservation_id=reservation_id,
            completed_at=completed_at,
            previous_receipt_hash=self._last_receipt_hash,
            success_evidence_code=success_evidence_code,
            billing_parent_id=reservation["billing_parent_id"],
        )
        delivery = None
        if self.receipt_sink is not None:
            delivery = self.receipt_sink.enqueue(
                receipt,
                event_id=f"enqueue:{reservation_id}",
                recorded_at=completed_at,
            )
        reservation.update({
            "state": "captured", "receipt": receipt,
            "receipt_delivery": delivery, "completed_at": completed_at,
        })
        self._last_receipt_hash = receipt["receipt_hash"]
        return copy.deepcopy(reservation)

    def release(self, *, reservation_id: str, reason_code: str, released_at: str) -> dict[str, Any]:
        reservation = self._reservation(reservation_id)
        if reservation["state"] == "released":
            return copy.deepcopy(reservation)
        if reservation["state"] in {"captured", "included"}:
            raise ValueError("reservation_not_releasable")
        photons = int(reservation["photons"])
        self.ledger.post(
            transaction_id=f"release:{reservation_id}",
            tenant_id=self.tenant_id,
            reason=_identifier(reason_code, "release_reason"),
            source_receipt_id=f"release:{reservation_id}",
            rate_card_version=self.price_book.version,
            idempotency_key=f"release:{reservation_id}",
            recorded_at=released_at,
            entries=[
                PhotonLedgerEntry("customer.reserved", -photons),
                PhotonLedgerEntry("customer.available", photons),
            ],
        )
        reservation.update({"state": "released", "released_at": released_at})
        return copy.deepcopy(reservation)

    def _reservation(self, reservation_id: str) -> dict[str, Any]:
        result = self._reservations.get(_identifier(reservation_id, "reservation_id"))
        if not result:
            raise KeyError("reservation_not_found")
        return result


def build_work_receipt(
    *,
    receipt_id: str,
    tenant_commitment: str,
    device_id: str,
    action_type: str,
    outcome_id: str,
    photons: int,
    rate_card_version: str,
    reservation_id: str,
    completed_at: str,
    previous_receipt_hash: str,
    success_evidence_code: str,
    billing_parent_id: str | None = None,
) -> dict[str, Any]:
    quantity = int(photons)
    if quantity < 0:
        raise ValueError("receipt_photon_quantity_invalid")
    previous_hash = previous_receipt_hash or "genesis"
    if previous_hash != "genesis" and not re.fullmatch(r"[0-9a-f]{64}", previous_hash):
        raise ValueError("previous_receipt_hash_invalid")
    payload = {
        "schema_version": WORK_RECEIPT_SCHEMA,
        "asset_namespace": PHOTON_ASSET_NAMESPACE,
        "receipt_id": _identifier(receipt_id, "receipt_id"),
        "tenant_commitment": _identifier(tenant_commitment, "tenant_commitment"),
        "device_id": _identifier(device_id, "device_id"),
        "action_type": _identifier(action_type, "action_type"),
        "outcome_id": _identifier(outcome_id, "outcome_id"),
        "photons": quantity,
        "rate_card_version": _identifier(rate_card_version, "rate_card_version"),
        "reservation_id": _identifier(reservation_id, "reservation_id"),
        "billing_parent_id": _identifier(billing_parent_id, "billing_parent_id") if billing_parent_id else None,
        "completed_at": completed_at,
        "previous_receipt_hash": previous_hash,
        "success_evidence_code": _identifier(success_evidence_code, "success_evidence_code"),
        "customer_content_included": False,
        "local_model_tokens_billed": False,
    }
    return {**payload, "receipt_hash": canonical_hash(payload)}
