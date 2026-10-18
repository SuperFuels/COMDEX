"""Content-minimising transaction policy for the shared GlyphChain ledger.

The ledger is a public/shared commitment boundary, not a Business Vault.  It
therefore accepts only the fixed fields needed to execute the small set of
supported transaction types.  Customer content and arbitrary extension JSON
must remain in Guardian and be represented here only by an approved hash or
opaque public identifier.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping

from backend.modules.chain_sim.document_proof import normalize_document_proof_payload


class LedgerContentPolicyError(ValueError):
    pass


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
_SAFE_DENOMINATION = re.compile(r"^[A-Za-z0-9._-]{1,32}$")
_EMAIL_LIKE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_FORBIDDEN_RESULT_KEYS = {
    "customer",
    "customer_name",
    "email",
    "phone",
    "billing_address",
    "service_address",
    "content",
    "document_content",
    "document_text",
    "message",
    "notes",
    "prompt",
    "invoice",
    "quotation",
    "quote",
    "file_path",
    "document_path",
    "secret",
    "password",
    "access_token",
    "refresh_token",
}


def _unexpected(payload: Mapping[str, Any], allowed: set[str]) -> None:
    extra = sorted(str(key) for key in payload if str(key) not in allowed)
    if extra:
        raise LedgerContentPolicyError(
            f"unsupported transaction payload fields: {', '.join(extra)}"
        )


def _identifier(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not _SAFE_IDENTIFIER.fullmatch(text):
        raise LedgerContentPolicyError(f"{field} contains unsupported characters or length")
    return text


def _denomination(value: Any) -> str:
    text = str(value or "").strip()
    if not _SAFE_DENOMINATION.fullmatch(text):
        raise LedgerContentPolicyError("denom contains unsupported characters or length")
    return text


def _amount(value: Any, field: str) -> str:
    text = str(value or "").strip()
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError):
        raise LedgerContentPolicyError(f"{field} must be a positive decimal amount") from None
    if not parsed.is_finite() or parsed <= 0 or len(text) > 96:
        raise LedgerContentPolicyError(f"{field} must be a positive bounded decimal amount")
    return text


def normalize_public_transaction_payload(tx_type: Any, payload: Any) -> Dict[str, Any]:
    """Return the only ledger-safe payload for ``tx_type`` or fail closed."""
    kind = str(tx_type or "").strip()
    if kind == "BANK_TRANSFER":
        kind = "BANK_SEND"
    if not isinstance(payload, Mapping):
        raise LedgerContentPolicyError("transaction payload must be an object")

    if kind in {"BANK_MINT", "BANK_SEND"}:
        _unexpected(payload, {"denom", "to", "amount"})
        return {
            "denom": _denomination(payload.get("denom")),
            "to": _identifier(payload.get("to"), "to"),
            "amount": _amount(payload.get("amount"), "amount"),
        }
    if kind == "BANK_BURN":
        _unexpected(payload, {"denom", "amount"})
        return {
            "denom": _denomination(payload.get("denom")),
            "amount": _amount(payload.get("amount"), "amount"),
        }
    if kind in {"STAKING_DELEGATE", "STAKING_UNDELEGATE"}:
        _unexpected(payload, {"validator", "amount_tess"})
        return {
            "validator": _identifier(payload.get("validator"), "validator"),
            "amount_tess": _amount(payload.get("amount_tess"), "amount_tess"),
        }
    if kind == "DOCUMENT_PROOF_V1":
        return normalize_document_proof_payload(payload)
    raise LedgerContentPolicyError("unsupported transaction type")


def assert_public_transaction_result(result: Any) -> Dict[str, Any]:
    """Reject free-form/private result material before it reaches SQLite."""
    if not isinstance(result, Mapping):
        raise LedgerContentPolicyError("transaction result must be an object")

    def visit(value: Any, path: str, depth: int) -> None:
        if depth > 8:
            raise LedgerContentPolicyError("transaction result nesting is too deep")
        if isinstance(value, Mapping):
            for key, child in value.items():
                key_text = str(key).strip().lower()
                if key_text in _FORBIDDEN_RESULT_KEYS:
                    raise LedgerContentPolicyError(
                        f"private result field is forbidden: {path}.{key_text}"
                    )
                visit(child, f"{path}.{key_text}", depth + 1)
        elif isinstance(value, (list, tuple)):
            if len(value) > 256:
                raise LedgerContentPolicyError("transaction result list is too large")
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]", depth + 1)
        elif isinstance(value, str):
            if len(value) > 256 or "\n" in value or "\r" in value or _EMAIL_LIKE.search(value):
                raise LedgerContentPolicyError(
                    f"free-form or personal text is forbidden: {path}"
                )
        elif value is not None and not isinstance(value, (bool, int, float)):
            raise LedgerContentPolicyError(f"unsupported transaction result value: {path}")

    projection = dict(result)
    visit(projection, "result", 0)
    encoded = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 64 * 1024:
        raise LedgerContentPolicyError("transaction result exceeds the public ledger limit")
    return projection
