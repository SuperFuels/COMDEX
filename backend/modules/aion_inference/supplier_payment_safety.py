"""Deterministic fail-closed boundary before supplier-payment cartridge execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Iterable, Mapping


_AMOUNT = re.compile(r"^(EUR|GBP|USD)\s+([0-9]+(?:\.[0-9]{1,2})?)$")
_INJECTION = re.compile(
    r"\b(ignore (?:all |the )?(?:previous|prior)|system prompt|developer message|"
    r"override (?:the )?(?:controls|policy)|bypass (?:the )?(?:controls|approval)|"
    r"do not verify|skip (?:verification|approval))\b",
    re.I,
)
_BANK_CHANGE = re.compile(
    r"\b(new|changed|updated|replacement|different|conflicting|mismatch(?:ed)?)\b"
    r".{0,32}\b(bank|account|iban|sort code|routing)\b|"
    r"\b(bank|account|iban|sort code|routing)\b.{0,32}"
    r"\b(new|changed|updated|replacement|different|conflicting|mismatch(?:ed)?)\b",
    re.I,
)


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class SupplierPaymentSafetyDecision:
    route: str
    safe_for_cartridge_execution: bool
    model_call_required: bool
    human_review_required: bool
    reasons: tuple[str, ...]
    canonical_fields: Mapping[str, str]
    proof_receipt: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_supplier_payment_request(
    *,
    public_request: str,
    extracted_fields: Mapping[str, str],
    active_tenant_id: str,
    requested_tenant_id: str,
    actor_role: str,
    known_invoice_references: Iterable[str] = (),
    role_limits: Mapping[str, str] | None = None,
    evidence_passages: Iterable[str] = (),
) -> SupplierPaymentSafetyDecision:
    reasons: list[str] = []
    fields = {key: str(value).strip() for key, value in extracted_fields.items() if str(value).strip()}
    required = {"supplier_name", "invoice_reference", "payment_amount"}
    if set(fields) != required:
        reasons.append("required_fields_not_exact")
    if not active_tenant_id or requested_tenant_id != active_tenant_id:
        reasons.append("tenant_binding_mismatch")

    combined_untrusted = "\n".join((public_request, *map(str, evidence_passages)))
    if _INJECTION.search(combined_untrusted):
        reasons.append("prompt_injection_detected")
    if _BANK_CHANGE.search(combined_untrusted):
        reasons.append("bank_detail_change_or_conflict")

    invoice = fields.get("invoice_reference", "").casefold()
    if invoice and invoice in {str(item).strip().casefold() for item in known_invoice_references}:
        reasons.append("duplicate_invoice_reference")

    amount = fields.get("payment_amount", "")
    match = _AMOUNT.fullmatch(amount)
    if not match:
        reasons.append("payment_amount_not_canonical")
    else:
        currency, numeric = match.groups()
        limit_text = (role_limits or {}).get(currency)
        if limit_text is None:
            reasons.append("role_limit_missing_for_currency")
        else:
            try:
                if Decimal(numeric) > Decimal(str(limit_text)):
                    reasons.append("role_limit_exceeded")
            except InvalidOperation:
                reasons.append("role_limit_invalid")

    reasons = list(dict.fromkeys(reasons))
    safe = not reasons
    payload = {
        "schema_version": "aion.supplier_payment_safety_receipt.v1",
        "active_tenant_id_sha256": hashlib.sha256(active_tenant_id.encode()).hexdigest(),
        "requested_tenant_id_sha256": hashlib.sha256(requested_tenant_id.encode()).hexdigest(),
        "actor_role": actor_role,
        "public_request_sha256": hashlib.sha256(public_request.encode()).hexdigest(),
        "evidence_set_sha256": hashlib.sha256(
            "\n".join(map(str, evidence_passages)).encode()
        ).hexdigest(),
        "canonical_fields": dict(sorted(fields.items())),
        "reasons": tuple(reasons),
        "safe_for_cartridge_execution": safe,
        "human_review_required": not safe,
        "model_calls": 0,
    }
    receipt = {**payload, "proof_receipt_sha256": _canonical_sha256(payload)}
    return SupplierPaymentSafetyDecision(
        route="verified_business_map" if safe else "human_review_required",
        safe_for_cartridge_execution=safe,
        model_call_required=False,
        human_review_required=not safe,
        reasons=tuple(reasons),
        canonical_fields=dict(sorted(fields.items())),
        proof_receipt=receipt,
    )
