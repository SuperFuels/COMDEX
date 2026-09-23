from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional
import time

from backend.modules.chain_sim.aion_proof_commit_store import (
    commit_aion_proof_record,
    get_aion_proof_commit_record,
    verify_aion_proof_commit_record,
)


AION_PROOF_RECEIPT_VERSION = "glyphchain.aion_proof_receipt.v0.1"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


@dataclass
class AionProofCommitReceipt:
    receipt_version: str
    proof_commitment_id: str
    proof_commitment_hash: str
    proof_type: str
    business_id: str
    job_id: str
    status: str
    verified: bool
    receipt_status: str
    created_at_ms: int = field(default_factory=_now_ms)
    block_height: Optional[int] = None
    tx_id: Optional[str] = None
    tx_hash: Optional[str] = None
    public_route_exposed: bool = False
    would_move_money: bool = False
    would_require_pho: bool = False
    would_require_token: bool = False
    would_require_wallet: bool = False
    would_create_payment: bool = False
    would_create_escrow: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_aion_proof_commit_receipt(record: Dict[str, Any], *, verified: bool) -> Dict[str, Any]:
    record = dict(record or {})

    receipt = AionProofCommitReceipt(
        receipt_version=AION_PROOF_RECEIPT_VERSION,
        proof_commitment_id=_clean_str(record.get("proof_commitment_id")),
        proof_commitment_hash=_clean_str(record.get("proof_commitment_hash")),
        proof_type=_clean_str(record.get("proof_type")),
        business_id=_clean_str(record.get("business_id")),
        job_id=_clean_str(record.get("job_id")),
        status=_clean_str(record.get("status") or "unknown"),
        verified=bool(verified),
        receipt_status="verified" if verified else "unverified",
        block_height=record.get("block_height"),
        tx_id=record.get("tx_id"),
        tx_hash=record.get("tx_hash"),
        public_route_exposed=False,
        would_move_money=False,
        would_require_pho=False,
        would_require_token=False,
        would_require_wallet=False,
        would_create_payment=False,
        would_create_escrow=False,
        metadata={"source": "aion_proof_commit_store"},
    )

    return receipt.to_dict()


def internal_commit_aion_proof_and_build_receipt(
    *,
    envelope: Dict[str, Any],
    proof_commitment_hash: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Internal/dev-safe route-shaped service.

    It commits a proof envelope into the dedicated AION proof store, then builds
    a receipt-shaped response.

    This does NOT expose a public FastAPI route.
    This does NOT submit a BANK_* tx.
    This does NOT move PHO, tokens, wallet state, payments, or escrow.
    """
    committed = commit_aion_proof_record(
        envelope=dict(envelope or {}),
        proof_commitment_hash=proof_commitment_hash,
        metadata=dict(metadata or {}),
    )

    if not committed.get("ok"):
        return {
            "ok": False,
            "status": "blocked",
            "blocked_reasons": list(committed.get("blocked_reasons") or []),
            "public_route_exposed": False,
            "would_move_money": False,
            "would_require_pho": False,
            "would_require_token": False,
            "would_require_wallet": False,
            "would_create_payment": False,
            "would_create_escrow": False,
        }

    record = dict(committed.get("record") or {})
    proof_commitment_id = _clean_str(committed.get("proof_commitment_id"))
    expected_hash = _clean_str(record.get("proof_commitment_hash"))

    verification = verify_aion_proof_commit_record(
        proof_commitment_id=proof_commitment_id,
        expected_proof_commitment_hash=expected_hash,
    )

    receipt = build_aion_proof_commit_receipt(
        record,
        verified=bool(verification.get("verified")),
    )

    return {
        "ok": True,
        "status": committed.get("status"),
        "proof_commitment_id": proof_commitment_id,
        "verified": bool(verification.get("verified")),
        "receipt": receipt,
        "record": record,
        "blocked_reasons": [],
    }


def internal_lookup_aion_proof_receipt(
    *,
    proof_commitment_id: str,
) -> Dict[str, Any]:
    """
    Internal/dev-safe receipt lookup.

    It returns the committed proof record and a receipt-shaped view.
    """
    found = get_aion_proof_commit_record(proof_commitment_id)

    if not found.get("ok"):
        return {
            "ok": False,
            "status": "not_found",
            "proof_commitment_id": _clean_str(proof_commitment_id),
            "verified": False,
            "receipt": None,
        }

    record = dict(found.get("record") or {})
    verification = verify_aion_proof_commit_record(
        proof_commitment_id=_clean_str(proof_commitment_id),
        expected_proof_commitment_hash=_clean_str(record.get("proof_commitment_hash")),
    )

    receipt = build_aion_proof_commit_receipt(
        record,
        verified=bool(verification.get("verified")),
    )

    return {
        "ok": True,
        "status": "found",
        "proof_commitment_id": _clean_str(proof_commitment_id),
        "verified": bool(verification.get("verified")),
        "receipt": receipt,
        "record": record,
    }


def internal_verify_aion_proof_receipt(
    *,
    proof_commitment_id: str,
    expected_proof_commitment_hash: str,
) -> Dict[str, Any]:
    """
    Internal/dev-safe verification wrapper.

    It verifies a stored proof commitment against an expected commitment hash and
    returns a receipt-shaped result.
    """
    verification = verify_aion_proof_commit_record(
        proof_commitment_id=_clean_str(proof_commitment_id),
        expected_proof_commitment_hash=_clean_str(expected_proof_commitment_hash),
    )

    if not verification.get("verified"):
        return {
            "ok": True,
            "status": verification.get("status"),
            "verified": False,
            "proof_commitment_id": _clean_str(proof_commitment_id),
            "expected_proof_commitment_hash": _clean_str(expected_proof_commitment_hash),
            "proof_commitment_hash": _clean_str(verification.get("proof_commitment_hash")),
            "receipt": None,
        }

    record = dict(verification.get("record") or {})
    receipt = build_aion_proof_commit_receipt(record, verified=True)

    return {
        "ok": True,
        "status": "verified",
        "verified": True,
        "proof_commitment_id": _clean_str(proof_commitment_id),
        "expected_proof_commitment_hash": _clean_str(expected_proof_commitment_hash),
        "proof_commitment_hash": _clean_str(verification.get("proof_commitment_hash")),
        "receipt": receipt,
        "record": record,
    }
