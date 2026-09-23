"""Narrow deterministic quotation drafting with mandatory human approval."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Mapping


_PATTERN = re.compile(
    r"^Prepare a draft quotation for (?P<job>[A-Za-z][A-Za-z0-9 &'\-]{1,80}): "
    r"base EUR (?P<base>[0-9]+(?:\.[0-9]{1,2})?), markup "
    r"(?P<markup>[0-9]+(?:\.[0-9]{1,2})?)%\. "
    r"Do not send it; human approval is required\.$",
    re.I,
)
_CONTRACT = {
    "schema_version": "aion.verified_quotation_contract.v1",
    "currency": "EUR",
    "base_range": ["0.01", "1000000.00"],
    "markup_range": ["0", "100"],
    "authority": {"send": False, "approve": False, "take_payment": False},
    "human_approval_required": True,
}
CONTRACT_SHA256 = hashlib.sha256(
    json.dumps(_CONTRACT, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class VerifiedQuotationDraft:
    route: str
    answer: str | None
    model_call_required: bool
    human_approval_required: bool
    send_allowed: bool
    payment_allowed: bool
    structured_result: Mapping[str, str] | None
    proof_receipt: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def draft_verified_quotation(text: str) -> VerifiedQuotationDraft | None:
    """Return a verified draft only for the complete bounded grammar."""
    match = _PATTERN.fullmatch(" ".join(text.split()))
    if match is None:
        return None
    try:
        base = Decimal(match.group("base"))
        markup = Decimal(match.group("markup"))
    except InvalidOperation:
        return None
    if not Decimal("0.01") <= base <= Decimal("1000000"):
        return None
    if not Decimal("0") <= markup <= Decimal("100"):
        return None
    total = (base * (Decimal("1") + markup / Decimal("100"))).quantize(
        Decimal("0.01")
    )
    recovered = total / (Decimal("1") + markup / Decimal("100"))
    inverse_verified = abs(recovered - base) <= Decimal("0.005")
    if not inverse_verified:
        return None
    job = match.group("job")
    base_text = f"{base:.2f}"
    markup_text = format(markup, "f")
    if "." in markup_text:
        markup_text = markup_text.rstrip("0").rstrip(".")
    total_text = f"{total:.2f}"
    answer = (
        f"DRAFT — {job}: base EUR {base_text}; markup {markup_text}%; "
        f"total EUR {total_text}. Not sent; human approval required."
    )
    structured = {
        "job": job,
        "currency": "EUR",
        "base": base_text,
        "markup_percent": markup_text,
        "total": total_text,
        "status": "draft_requires_human_approval",
    }
    payload = {
        "schema_version": "aion.verified_quotation_receipt.v1",
        "contract_sha256": CONTRACT_SHA256,
        "request_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
        "structured_result": structured,
        "inverse_verified": inverse_verified,
        "model_calls": 0,
        "send_allowed": False,
        "payment_allowed": False,
        "human_approval_required": True,
    }
    receipt = {**payload, "proof_receipt_sha256": _canonical_sha256(payload)}
    return VerifiedQuotationDraft(
        route="verified_quotation_atomsheet",
        answer=answer,
        model_call_required=False,
        human_approval_required=True,
        send_allowed=False,
        payment_allowed=False,
        structured_result=structured,
        proof_receipt=receipt,
    )
