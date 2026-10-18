from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json


EVIDENCE_SCHEMA_VERSION = "aion.gateway.evidence.v0.1"
JOB_PROOF_SCHEMA_VERSION = "aion.gateway.job_proof.v0.1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass
class EvidenceItem:
    evidence_id: str
    evidence_type: str
    source: str
    captured_at: str
    provenance: Dict[str, Any] = field(default_factory=dict)
    payload_ref: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    freshness: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = EVIDENCE_SCHEMA_VERSION

    def to_hash_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source": self.source,
            "captured_at": self.captured_at,
            "provenance": dict(self.provenance or {}),
            "payload_ref": dict(self.payload_ref or {}),
            "confidence": float(self.confidence or 0.0),
            "freshness": self.freshness,
            "metadata": dict(self.metadata or {}),
        }

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["evidence_hash"] = hash_evidence_item(self)
        return data


def hash_evidence_item(item: EvidenceItem | Dict[str, Any]) -> str:
    if isinstance(item, EvidenceItem):
        payload = item.to_hash_payload()
    else:
        payload = {
            "schema_version": item.get("schema_version") or EVIDENCE_SCHEMA_VERSION,
            "evidence_id": item.get("evidence_id") or "",
            "evidence_type": item.get("evidence_type") or "",
            "source": item.get("source") or "",
            "captured_at": item.get("captured_at") or "",
            "provenance": dict(item.get("provenance") or {}),
            "payload_ref": dict(item.get("payload_ref") or {}),
            "confidence": float(item.get("confidence") or 0.0),
            "freshness": item.get("freshness") or "unknown",
            "metadata": dict(item.get("metadata") or {}),
        }
    return stable_sha256(payload)


def build_evidence_item(
    *,
    evidence_id: str,
    evidence_type: str,
    source: str,
    captured_at: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
    payload_ref: Optional[Dict[str, Any]] = None,
    confidence: float = 0.0,
    freshness: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    item = EvidenceItem(
        evidence_id=str(evidence_id or ""),
        evidence_type=str(evidence_type or ""),
        source=str(source or ""),
        captured_at=captured_at or utc_now_iso(),
        provenance=dict(provenance or {}),
        payload_ref=dict(payload_ref or {}),
        confidence=float(confidence or 0.0),
        freshness=str(freshness or "unknown"),
        metadata=dict(metadata or {}),
    )
    return item.to_dict()


def build_job_proof_hash(
    *,
    job: Dict[str, Any],
    evidence_items: Optional[List[Dict[str, Any]]] = None,
    timeline: Optional[List[Dict[str, Any]]] = None,
    settlement_readiness: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    evidence_items = list(evidence_items or [])
    timeline = list(timeline or [])

    normalized_evidence = []
    for item in evidence_items:
        row = dict(item)

        # Recalculate from canonical evidence content every time.
        # A stale caller-provided evidence_hash MUST NOT mask changed evidence.
        row["evidence_hash"] = hash_evidence_item(row)
        normalized_evidence.append(row)

    evidence_hashes = sorted(str(item.get("evidence_hash") or "") for item in normalized_evidence)

    proof_payload = {
        "schema_version": JOB_PROOF_SCHEMA_VERSION,
        "job": dict(job or {}),
        "evidence_hashes": evidence_hashes,
        "timeline": timeline,
        "settlement_readiness": dict(settlement_readiness or {}),
    }

    return {
        "schema_version": JOB_PROOF_SCHEMA_VERSION,
        "proof_type": "job_proof_hash",
        "job_id": str((job or {}).get("job_id") or ""),
        "evidence_count": len(normalized_evidence),
        "evidence_hashes": evidence_hashes,
        "job_proof_hash": stable_sha256(proof_payload),
        "proof_payload": proof_payload,
        "dry_run_only": True,
        "would_commit_to_glyphchain": False,
        "would_create_payment": False,
        "would_grant_permission": False,
    }
