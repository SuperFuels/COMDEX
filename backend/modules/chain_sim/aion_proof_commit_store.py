from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import time

from backend.modules.chain_sim.canonical_codec import canonical_hash_hex


AION_PROOF_COMMIT_STORE_VERSION = "glyphchain.aion_proof_commit_store.v0.1"

SUPPORTED_AION_PROOF_TYPES = {
    "AION_JOB_PROOF_V1",
    "AION_EVIDENCE_PROOF_V1",
    "AION_SETTLEMENT_READINESS_PROOF_V1",
}

_PROOF_COMMITMENTS: Dict[str, Dict[str, Any]] = {}


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _canonical_hash(payload: Dict[str, Any]) -> str:
    return canonical_hash_hex(payload)


@dataclass
class AionProofCommitRecord:
    proof_commitment_id: str
    store_version: str
    proof_type: str
    business_id: str
    job_id: str
    proof_payload_hash: str
    proof_commitment_hash: str
    envelope: Dict[str, Any]
    status: str = "committed"
    committed_at_ms: int = field(default_factory=_now_ms)
    block_height: Optional[int] = None
    tx_id: Optional[str] = None
    tx_hash: Optional[str] = None
    dry_run_chain_tx: bool = True
    would_move_money: bool = False
    would_require_pho: bool = False
    would_require_token: bool = False
    would_require_wallet: bool = False
    would_create_payment: bool = False
    would_create_escrow: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def reset_aion_proof_commit_store() -> None:
    _PROOF_COMMITMENTS.clear()


def build_aion_proof_commitment_id(
    *,
    proof_type: str,
    business_id: str,
    job_id: str,
    proof_commitment_hash: str,
) -> str:
    h = _canonical_hash(
        {
            "store_version": AION_PROOF_COMMIT_STORE_VERSION,
            "proof_type": _clean_str(proof_type),
            "business_id": _clean_str(business_id).lower(),
            "job_id": _clean_str(job_id),
            "proof_commitment_hash": _clean_str(proof_commitment_hash),
        }
    )
    return f"aion_proof_{h[:24]}"


def commit_aion_proof_record(
    *,
    envelope: Dict[str, Any],
    proof_commitment_hash: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    env = dict(envelope or {})
    blocked: List[str] = []

    proof_type = _clean_str(env.get("proof_type"))
    business_id = _clean_str(env.get("business_id")).lower()
    job_id = _clean_str(env.get("job_id"))
    payload_hash = _clean_str(env.get("proof_payload_hash"))
    commitment_hash = _clean_str(proof_commitment_hash)

    if proof_type not in SUPPORTED_AION_PROOF_TYPES:
        blocked.append("unsupported_proof_type")
    if not business_id:
        blocked.append("missing_business_id")
    if not job_id:
        blocked.append("missing_job_id")
    if not payload_hash:
        blocked.append("missing_proof_payload_hash")
    if not commitment_hash:
        blocked.append("missing_proof_commitment_hash")

    if env.get("would_move_money") is True:
        blocked.append("proof_commit_must_not_move_money")
    if env.get("would_require_pho") is True:
        blocked.append("proof_commit_must_not_require_pho")
    if env.get("would_require_token") is True:
        blocked.append("proof_commit_must_not_require_token")
    if env.get("would_require_wallet") is True:
        blocked.append("proof_commit_must_not_require_wallet")
    if env.get("would_create_payment") is True:
        blocked.append("proof_commit_must_not_create_payment")
    if env.get("would_create_escrow") is True:
        blocked.append("proof_commit_must_not_create_escrow")

    if blocked:
        return {
            "ok": False,
            "status": "blocked",
            "blocked_reasons": blocked,
            "would_move_money": False,
            "would_require_pho": False,
            "would_require_token": False,
            "would_require_wallet": False,
            "would_create_payment": False,
            "would_create_escrow": False,
        }

    proof_commitment_id = build_aion_proof_commitment_id(
        proof_type=proof_type,
        business_id=business_id,
        job_id=job_id,
        proof_commitment_hash=commitment_hash,
    )

    existing = _PROOF_COMMITMENTS.get(proof_commitment_id)
    if existing:
        return {
            "ok": True,
            "status": "already_committed",
            "proof_commitment_id": proof_commitment_id,
            "record": dict(existing),
            "blocked_reasons": [],
        }

    record = AionProofCommitRecord(
        proof_commitment_id=proof_commitment_id,
        store_version=AION_PROOF_COMMIT_STORE_VERSION,
        proof_type=proof_type,
        business_id=business_id,
        job_id=job_id,
        proof_payload_hash=payload_hash,
        proof_commitment_hash=commitment_hash,
        envelope=env,
        metadata=dict(metadata or {}),
    ).to_dict()

    _PROOF_COMMITMENTS[proof_commitment_id] = record

    return {
        "ok": True,
        "status": "committed",
        "proof_commitment_id": proof_commitment_id,
        "record": dict(record),
        "blocked_reasons": [],
    }


def get_aion_proof_commit_record(proof_commitment_id: str) -> Dict[str, Any]:
    proof_commitment_id = _clean_str(proof_commitment_id)
    record = _PROOF_COMMITMENTS.get(proof_commitment_id)
    if not record:
        return {
            "ok": False,
            "status": "not_found",
            "proof_commitment_id": proof_commitment_id,
        }
    return {
        "ok": True,
        "status": "found",
        "proof_commitment_id": proof_commitment_id,
        "record": dict(record),
    }


def verify_aion_proof_commit_record(
    *,
    proof_commitment_id: str,
    expected_proof_commitment_hash: Optional[str] = None,
) -> Dict[str, Any]:
    found = get_aion_proof_commit_record(proof_commitment_id)
    if not found.get("ok"):
        return {
            "ok": True,
            "verified": False,
            "status": "not_found",
            "proof_commitment_id": proof_commitment_id,
        }

    record = dict(found["record"])
    expected = _clean_str(expected_proof_commitment_hash or record.get("proof_commitment_hash"))
    actual = _clean_str(record.get("proof_commitment_hash"))

    verified = bool(expected and actual and expected == actual)

    return {
        "ok": True,
        "verified": verified,
        "status": "verified" if verified else "failed",
        "proof_commitment_id": proof_commitment_id,
        "proof_commitment_hash": actual,
        "expected_proof_commitment_hash": expected,
        "record": record,
    }


def list_aion_proof_commit_records() -> Dict[str, Any]:
    records = list(_PROOF_COMMITMENTS.values())
    records.sort(key=lambda r: int(r.get("committed_at_ms") or 0))
    return {
        "ok": True,
        "count": len(records),
        "records": records,
    }
