"""Verified bounded extraction of supplier-payment fields without a model call."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Mapping


_NAME = r"(?P<supplier>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 &'\-]{1,100}?)"
_INVOICE = r"(?P<invoice>[A-Z]{2,5}-[0-9]{2,6})"
_PAYMENT = r"(?P<currency>EUR|USD|GBP|SEK) (?P<amount>[0-9]+\.[0-9]{2})"
_PATTERNS = tuple(
    (pattern_id, re.compile(pattern))
    for pattern_id, pattern in (
        ("review_payment_to", rf"^Review payment to {_NAME} for invoice {_INVOICE}, amount {_PAYMENT}\.$"),
        ("supplier_submitted", rf"^Supplier {_NAME} submitted invoice {_INVOICE} for {_PAYMENT}\.$"),
        ("please_review_from", rf"^Please review invoice {_INVOICE} from {_NAME} for {_PAYMENT}\.$"),
        ("payment_review", rf"^Payment review: {_NAME}, invoice {_INVOICE}, {_PAYMENT}\.$"),
        ("check_before_paying", rf"^Check {_NAME} invoice {_INVOICE} before paying {_PAYMENT}\.$"),
        ("vendor_requests", rf"^Vendor {_NAME} requests {_PAYMENT} against invoice {_INVOICE}\.$"),
        ("review_amount_from", rf"^Review {_PAYMENT} for invoice {_INVOICE} from {_NAME}\.$"),
        ("invoice_awaiting_review", rf"^Invoice {_INVOICE} from {_NAME} is awaiting review for {_PAYMENT}\.$"),
    )
)
_CONTRACT = {
    "schema_version": "aion.verified_supplier_extraction_contract.v1",
    "pattern_ids": [item[0] for item in _PATTERNS],
    "currencies": ["EUR", "GBP", "SEK", "USD"],
    "amount_range": ["0.01", "1000000.00"],
    "invoice_pattern": "[A-Z]{2,5}-[0-9]{2,6}",
    "supplier_pattern": "[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 &'\\-]{1,100}?",
    "required_invoice_matches": 1,
    "required_payment_matches": 1,
    "authority": {"approve": False, "execute_payment": False},
}
CONTRACT_SHA256 = hashlib.sha256(
    json.dumps(_CONTRACT, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class VerifiedSupplierExtraction:
    route: str
    fields: Mapping[str, str]
    model_call_required: bool
    payment_execution_allowed: bool
    proof_receipt: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_verified_supplier_fields(text: str) -> VerifiedSupplierExtraction | None:
    """Extract only when one complete contract pattern and every bound validates."""
    normalized = " ".join(text.split())
    if len(re.findall(r"\b[A-Z]{2,5}-[0-9]{2,6}\b", normalized)) != 1:
        return None
    if len(re.findall(r"\b(?:EUR|USD|GBP|SEK) [0-9]+\.[0-9]{2}\b", normalized)) != 1:
        return None
    matches = [(pattern_id, match) for pattern_id, pattern in _PATTERNS
               if (match := pattern.fullmatch(normalized)) is not None]
    if len(matches) != 1:
        return None
    pattern_id, match = matches[0]
    supplier = match.group("supplier").strip()
    invoice = match.group("invoice")
    currency = match.group("currency")
    amount_text = match.group("amount")
    if re.search(r"\b(?:ignore|execute|approve|transfer|send|other tenant|other company)\b",
                 supplier, re.I):
        return None
    try:
        amount = Decimal(amount_text)
    except InvalidOperation:
        return None
    if not Decimal("0.01") <= amount <= Decimal("1000000.00"):
        return None
    fields = {
        "supplier_name": supplier,
        "invoice_reference": invoice,
        "payment_amount": f"{currency} {amount:.2f}",
    }
    payload = {
        "schema_version": "aion.verified_supplier_extraction_receipt.v1",
        "contract_sha256": CONTRACT_SHA256,
        "pattern_id": pattern_id,
        "request_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "fields": fields,
        "fields_sha256": _canonical_sha256(fields),
        "model_calls": 0,
        "payment_execution_allowed": False,
    }
    receipt = {**payload, "proof_receipt_sha256": _canonical_sha256(payload)}
    return VerifiedSupplierExtraction(
        route="verified_supplier_extraction_atomsheet",
        fields=fields,
        model_call_required=False,
        payment_execution_allowed=False,
        proof_receipt=receipt,
    )
