from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import time

from backend.modules.chain_sim.canonical_codec import canonical_hash_hex


PROOF_PROTOCOL_VERSION = "aion.glyphchain_proof_commit.v0.1"

AION_JOB_PROOF_V1 = "AION_JOB_PROOF_V1"
AION_EVIDENCE_PROOF_V1 = "AION_EVIDENCE_PROOF_V1"
AION_SETTLEMENT_READINESS_PROOF_V1 = "AION_SETTLEMENT_READINESS_PROOF_V1"

SUPPORTED_PROOF_TYPES = {
    AION_JOB_PROOF_V1,
    AION_EVIDENCE_PROOF_V1,
    AION_SETTLEMENT_READINESS_PROOF_V1,
}


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _hash_payload(payload: Dict[str, Any]) -> str:
    return canonical_hash_hex(payload)


@dataclass
class AionGlyphChainProofEnvelope:
    proof_protocol_version: str
    proof_type: str
    business_id: str
    job_id: str
    proof_payload: Dict[str, Any]
    proof_payload_hash: str
    dry_run_only: bool = True
    would_submit_chain_tx: bool = False
    would_move_money: bool = False
    would_require_pho: bool = False
    would_require_token: bool = False
    would_require_wallet: bool = False
    would_create_payment: bool = False
    would_create_escrow: bool = False
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GlyphChainProofCommitPreview:
    ok: bool
    proof_protocol_version: str
    envelope: Dict[str, Any]
    glyphchain_commit_status: str
    proof_commitment_hash: str
    blocked_reasons: List[str] = field(default_factory=list)
    safety: Dict[str, Any] = field(default_factory=dict)
    chain_sim: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_aion_proof_envelope(
    *,
    proof_type: str,
    business_id: str,
    job_id: str,
    proof_payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    proof_type_norm = _clean_str(proof_type)
    business_id_norm = _clean_str(business_id).lower()
    job_id_norm = _clean_str(job_id)

    payload = dict(proof_payload or {})

    envelope = AionGlyphChainProofEnvelope(
        proof_protocol_version=PROOF_PROTOCOL_VERSION,
        proof_type=proof_type_norm,
        business_id=business_id_norm,
        job_id=job_id_norm,
        proof_payload=payload,
        proof_payload_hash=_hash_payload(
            {
                "proof_protocol_version": PROOF_PROTOCOL_VERSION,
                "proof_type": proof_type_norm,
                "business_id": business_id_norm,
                "job_id": job_id_norm,
                "proof_payload": payload,
            }
        ),
        metadata=dict(metadata or {}),
    )

    return envelope.to_dict()


def preview_glyphchain_proof_commit(
    *,
    proof_type: str,
    business_id: str,
    job_id: str,
    proof_payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blocked: List[str] = []

    proof_type_norm = _clean_str(proof_type)
    if proof_type_norm not in SUPPORTED_PROOF_TYPES:
        blocked.append("unsupported_proof_type")

    if not _clean_str(business_id):
        blocked.append("missing_business_id")

    if not _clean_str(job_id):
        blocked.append("missing_job_id")

    if not isinstance(proof_payload, dict) or not proof_payload:
        blocked.append("missing_proof_payload")

    envelope = build_aion_proof_envelope(
        proof_type=proof_type_norm,
        business_id=business_id,
        job_id=job_id,
        proof_payload=proof_payload if isinstance(proof_payload, dict) else {},
        metadata=metadata,
    )

    proof_commitment_hash = _hash_payload(
        {
            "commit_protocol": PROOF_PROTOCOL_VERSION,
            "chain": "glyphchain",
            "mode": "dry_run_preview",
            "envelope": envelope,
        }
    )

    return GlyphChainProofCommitPreview(
        ok=not bool(blocked),
        proof_protocol_version=PROOF_PROTOCOL_VERSION,
        envelope=envelope,
        glyphchain_commit_status="dry_run_preview_only" if not blocked else "blocked",
        proof_commitment_hash=proof_commitment_hash,
        blocked_reasons=blocked,
        safety={
            "dry_run_only": True,
            "would_submit_chain_tx": False,
            "would_move_money": False,
            "would_require_pho": False,
            "would_require_token": False,
            "would_require_wallet": False,
            "would_create_payment": False,
            "would_create_escrow": False,
            "uses_existing_chain_sim_canonical_codec": True,
        },
        chain_sim={
            "module": "backend.modules.chain_sim",
            "canonical_codec": "backend.modules.chain_sim.canonical_codec.canonical_hash_hex",
            "live_tx_submit": False,
            "reason": "ChainSim live tx types are currently bank/staking only; AION proof commit remains dry-run adapter v0.",
        },
    ).to_dict()


def preview_job_proof_commit(
    *,
    business_id: str,
    job_id: str,
    job_proof_hash: str,
    evidence_proof_hashes: Optional[List[str]] = None,
    settlement_readiness_proof_hash: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return preview_glyphchain_proof_commit(
        proof_type=AION_JOB_PROOF_V1,
        business_id=business_id,
        job_id=job_id,
        proof_payload={
            "job_proof_hash": _clean_str(job_proof_hash),
            "evidence_proof_hashes": list(evidence_proof_hashes or []),
            "settlement_readiness_proof_hash": _clean_str(settlement_readiness_proof_hash),
        },
        metadata=metadata,
    )


def verify_aion_proof_commitment(
    *,
    envelope: Dict[str, Any],
    proof_commitment_hash: str,
) -> Dict[str, Any]:
    env = dict(envelope or {})
    blocked: List[str] = []

    proof_type = _clean_str(env.get("proof_type"))
    if proof_type not in SUPPORTED_PROOF_TYPES:
        blocked.append("unsupported_proof_type")

    proof_payload = env.get("proof_payload")
    if not isinstance(proof_payload, dict) or not proof_payload:
        blocked.append("missing_proof_payload")
        proof_payload = {}

    recomputed_payload_hash = _hash_payload(
        {
            "proof_protocol_version": _clean_str(env.get("proof_protocol_version")),
            "proof_type": proof_type,
            "business_id": _clean_str(env.get("business_id")).lower(),
            "job_id": _clean_str(env.get("job_id")),
            "proof_payload": dict(proof_payload),
        }
    )

    payload_hash_matches = recomputed_payload_hash == _clean_str(env.get("proof_payload_hash"))

    recomputed_commitment_hash = _hash_payload(
        {
            "commit_protocol": PROOF_PROTOCOL_VERSION,
            "chain": "glyphchain",
            "mode": "dry_run_preview",
            "envelope": env,
        }
    )

    commitment_hash_matches = recomputed_commitment_hash == _clean_str(proof_commitment_hash)

    verified = (
        not blocked
        and payload_hash_matches
        and commitment_hash_matches
        and bool(env.get("dry_run_only") is True)
        and bool(env.get("would_submit_chain_tx") is False)
        and bool(env.get("would_move_money") is False)
    )

    return {
        "ok": True,
        "verified": bool(verified),
        "proof_type": proof_type,
        "payload_hash_matches": bool(payload_hash_matches),
        "commitment_hash_matches": bool(commitment_hash_matches),
        "recomputed_payload_hash": recomputed_payload_hash,
        "recomputed_commitment_hash": recomputed_commitment_hash,
        "blocked_reasons": blocked,
        "safety": {
            "dry_run_only": bool(env.get("dry_run_only") is True),
            "would_submit_chain_tx": bool(env.get("would_submit_chain_tx") is True),
            "would_move_money": bool(env.get("would_move_money") is True),
            "would_require_pho": bool(env.get("would_require_pho") is True),
            "would_require_token": bool(env.get("would_require_token") is True),
            "would_require_wallet": bool(env.get("would_require_wallet") is True),
        },
    }
