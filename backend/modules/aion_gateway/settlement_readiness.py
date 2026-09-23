from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json


SETTLEMENT_SCHEMA_VERSION = "aion.gateway.settlement_readiness.v0.1"

SETTLEMENT_STATES = {
    "not_requested",
    "payment_requested",
    "deposit_paid",
    "payment_ready",
    "disputed",
    "refund_recommended",
}

PAYMENT_MODES = {
    "cash",
    "bank_transfer",
    "card",
    "stripe",
    "revolut",
    "invoice",
    "paypal",
    "other_fiat",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stable_fiat_payment_reference_hash(
    *,
    business_id: str,
    job_id: str,
    payment_reference: str = "",
    payment_mode: str = "",
    amount: Optional[float] = None,
    currency: str = "EUR",
) -> str:
    payload = {
        "schema_version": SETTLEMENT_SCHEMA_VERSION,
        "hash_type": "fiat_payment_reference_hash",
        "business_id": str(business_id or "").lower(),
        "job_id": str(job_id or ""),
        "payment_reference": str(payment_reference or ""),
        "payment_mode": str(payment_mode or "").lower(),
        "amount": amount,
        "currency": str(currency or "EUR").upper(),
    }
    return canonical_json_hash(payload)


@dataclass
class SettlementReadiness:
    job_id: str
    business_id: str
    state: str = "not_requested"

    payment_requested: bool = False
    deposit_paid: bool = False
    payment_ready: bool = False
    disputed: bool = False
    refund_recommended: bool = False

    payment_mode: str = "other_fiat"
    currency: str = "EUR"
    quoted_amount: Optional[float] = None
    deposit_amount: Optional[float] = None
    final_amount_due: Optional[float] = None
    payment_reference: str = ""

    fiat_payment_reference_hash: str = ""
    settlement_readiness_hash: str = ""

    blocked_reasons: List[str] = field(default_factory=list)
    proof_ready: bool = False
    dry_run_only: bool = True
    would_move_money: bool = False
    would_create_payment: bool = False
    would_create_escrow: bool = False
    would_commit_glyphchain: bool = False
    requires_human_review: bool = True

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    schema_version: str = SETTLEMENT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_settlement_readiness(
    *,
    job_id: str,
    business_id: str,
    state: str = "not_requested",
    payment_requested: bool = False,
    deposit_paid: bool = False,
    payment_ready: bool = False,
    disputed: bool = False,
    refund_recommended: bool = False,
    payment_mode: str = "other_fiat",
    currency: str = "EUR",
    quoted_amount: Optional[float] = None,
    deposit_amount: Optional[float] = None,
    final_amount_due: Optional[float] = None,
    payment_reference: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blocked_reasons: List[str] = []

    job_id = str(job_id or "").strip()
    business_id = str(business_id or "").strip()
    state = str(state or "not_requested").strip()
    payment_mode = str(payment_mode or "other_fiat").strip().lower()
    currency = str(currency or "EUR").strip().upper()

    if not job_id:
        blocked_reasons.append("missing_job_id")
    if not business_id:
        blocked_reasons.append("missing_business_id")
    if state not in SETTLEMENT_STATES:
        blocked_reasons.append("invalid_settlement_state")
    if payment_mode not in PAYMENT_MODES:
        blocked_reasons.append("unsupported_payment_mode")

    # Derived consistency checks.
    if payment_ready and disputed:
        blocked_reasons.append("payment_ready_conflicts_with_disputed")
    if refund_recommended and not disputed:
        blocked_reasons.append("refund_recommended_requires_disputed")

    fiat_hash = stable_fiat_payment_reference_hash(
        business_id=business_id,
        job_id=job_id,
        payment_reference=payment_reference,
        payment_mode=payment_mode,
        amount=final_amount_due if final_amount_due is not None else quoted_amount,
        currency=currency,
    )

    readiness_payload = {
        "schema_version": SETTLEMENT_SCHEMA_VERSION,
        "hash_type": "settlement_readiness_hash",
        "job_id": job_id,
        "business_id": business_id.lower(),
        "state": state,
        "payment_requested": bool(payment_requested),
        "deposit_paid": bool(deposit_paid),
        "payment_ready": bool(payment_ready),
        "disputed": bool(disputed),
        "refund_recommended": bool(refund_recommended),
        "payment_mode": payment_mode,
        "currency": currency,
        "quoted_amount": quoted_amount,
        "deposit_amount": deposit_amount,
        "final_amount_due": final_amount_due,
        "fiat_payment_reference_hash": fiat_hash,
        "blocked_reasons": list(blocked_reasons),
    }

    readiness_hash = canonical_json_hash(readiness_payload)

    proof_ready = bool(
        not blocked_reasons
        and (payment_ready or disputed or refund_recommended or deposit_paid or payment_requested)
    )

    result = SettlementReadiness(
        job_id=job_id,
        business_id=business_id,
        state=state,
        payment_requested=bool(payment_requested),
        deposit_paid=bool(deposit_paid),
        payment_ready=bool(payment_ready),
        disputed=bool(disputed),
        refund_recommended=bool(refund_recommended),
        payment_mode=payment_mode,
        currency=currency,
        quoted_amount=quoted_amount,
        deposit_amount=deposit_amount,
        final_amount_due=final_amount_due,
        payment_reference=payment_reference,
        fiat_payment_reference_hash=fiat_hash,
        settlement_readiness_hash=readiness_hash,
        blocked_reasons=blocked_reasons,
        proof_ready=proof_ready,
        dry_run_only=True,
        would_move_money=False,
        would_create_payment=False,
        would_create_escrow=False,
        would_commit_glyphchain=False,
        requires_human_review=True,
        metadata={
            **dict(metadata or {}),
            "fiat_first": True,
            "proof_only": True,
            "glyphchain_payment_rail": False,
            "requires_wallet": False,
            "requires_token": False,
            "requires_pho": False,
        },
    )

    return result.to_dict()
