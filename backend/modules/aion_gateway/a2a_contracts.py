from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import hashlib
import json
import time


A2A_CONTRACT_SCHEMA_VERSION = "aion.a2a.contracts.v0.1"


def utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stable_contract_hash(contract_type: str, payload: Dict[str, Any]) -> str:
    """
    Deterministic hash for replay, evidence, trace, and future GlyphChain anchoring.

    The hash is not a permission grant and must not trigger execution.
    """
    body = {
        "schema_version": A2A_CONTRACT_SCHEMA_VERSION,
        "contract_type": str(contract_type or "").lower(),
        "payload": payload or {},
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass
class CapabilityContract:
    business_id: str
    service_types: List[str]
    locations: List[str]
    can_quote: bool = True
    can_schedule: bool = False
    can_take_payment: bool = False
    can_provide_evidence: bool = True
    limitations: List[str] = field(default_factory=list)
    schema_version: str = A2A_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_type"] = "capability"
        data["contract_hash"] = stable_contract_hash("capability", data)
        return data


@dataclass
class AvailabilityContract:
    business_id: str
    service_type: str
    location: str
    availability_status: str = "unknown"
    earliest_available_at: Optional[str] = None
    estimated_response_minutes: Optional[int] = None
    blockers: List[str] = field(default_factory=list)
    schema_version: str = A2A_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_type"] = "availability"
        data["contract_hash"] = stable_contract_hash("availability", data)
        return data


@dataclass
class QuoteContract:
    business_id: str
    job_id: str
    fiat_currency: str
    quoted_amount: float
    assumptions: List[str] = field(default_factory=list)
    expires_at: Optional[str] = None
    requires_human_acceptance: bool = True
    schema_version: str = A2A_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_type"] = "quote"
        data["contract_hash"] = stable_contract_hash("quote", data)
        return data


@dataclass
class ExecutionContract:
    business_id: str
    job_id: str
    workflow_run_id: Optional[str] = None
    goal_id: Optional[str] = None
    stages: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    requires_human_review: bool = True
    dry_run_first: bool = True
    schema_version: str = A2A_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_type"] = "execution"
        data["contract_hash"] = stable_contract_hash("execution", data)
        return data


@dataclass
class TraceContract:
    business_id: str
    job_id: str
    current_stage: str
    next_expected_event: str
    blocked_reason: str = ""
    workflow_run_id: Optional[str] = None
    goal_id: Optional[str] = None
    evidence_state: str = "not_started"
    approval_state: str = "human_review_required"
    exception_state: str = "none"
    settlement_readiness_state: str = "not_ready"
    proof_commitment_state: str = "not_committed"
    schema_version: str = A2A_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_type"] = "trace"
        data["contract_hash"] = stable_contract_hash("trace", data)
        return data


@dataclass
class EvidenceContract:
    business_id: str
    job_id: str
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    required_evidence: List[str] = field(default_factory=list)
    evidence_confidence: float = 0.0
    evidence_freshness: str = "unknown"
    evidence_provenance: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = A2A_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_type"] = "evidence"
        data["contract_hash"] = stable_contract_hash("evidence", data)
        return data


@dataclass
class ExceptionContract:
    business_id: str
    job_id: str
    exception_type: str
    severity: str = "medium"
    recovery_actions: List[str] = field(default_factory=list)
    requires_human_review: bool = True
    resolved: bool = False
    schema_version: str = A2A_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_type"] = "exception"
        data["contract_hash"] = stable_contract_hash("exception", data)
        return data


@dataclass
class SettlementReadinessContract:
    business_id: str
    job_id: str
    payment_requested: bool = False
    deposit_paid: bool = False
    payment_ready: bool = False
    disputed: bool = False
    refund_recommended: bool = False
    fiat_payment_reference_hash: Optional[str] = None
    requires_crypto_payment: bool = False
    schema_version: str = A2A_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_type"] = "settlement_readiness"
        data["contract_hash"] = stable_contract_hash("settlement_readiness", data)
        return data


@dataclass
class ProofCommitmentContract:
    business_id: str
    job_id: str
    job_proof_hash: str
    evidence_proof_hashes: List[str] = field(default_factory=list)
    settlement_readiness_proof_hash: Optional[str] = None
    glyphchain_commit_status: str = "not_committed"
    glyphchain_commit_id: Optional[str] = None
    proof_is_payment: bool = False
    schema_version: str = A2A_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_type"] = "proof_commitment"
        data["contract_hash"] = stable_contract_hash("proof_commitment", data)
        return data


def build_empty_a2a_contract_bundle(*, business_id: str, job_id: str) -> Dict[str, Any]:
    """
    Build a safe schema-first A2A contract bundle.

    This does not expose routes, create jobs, execute workflows, take payments,
    commit proofs, or grant permissions.
    """
    bundle = {
        "schema_version": A2A_CONTRACT_SCHEMA_VERSION,
        "business_id": business_id,
        "job_id": job_id,
        "created_at": utc_now_iso(),
        "dry_run_only": True,
        "contracts": {
            "capability": CapabilityContract(
                business_id=business_id,
                service_types=[],
                locations=[],
            ).to_dict(),
            "availability": AvailabilityContract(
                business_id=business_id,
                service_type="unknown",
                location="unknown",
            ).to_dict(),
            "quote": QuoteContract(
                business_id=business_id,
                job_id=job_id,
                fiat_currency="EUR",
                quoted_amount=0.0,
            ).to_dict(),
            "execution": ExecutionContract(
                business_id=business_id,
                job_id=job_id,
            ).to_dict(),
            "trace": TraceContract(
                business_id=business_id,
                job_id=job_id,
                current_stage="requested",
                next_expected_event="human_review",
            ).to_dict(),
            "evidence": EvidenceContract(
                business_id=business_id,
                job_id=job_id,
            ).to_dict(),
            "exception": ExceptionContract(
                business_id=business_id,
                job_id=job_id,
                exception_type="none",
                severity="none",
            ).to_dict(),
            "settlement_readiness": SettlementReadinessContract(
                business_id=business_id,
                job_id=job_id,
            ).to_dict(),
            "proof_commitment": ProofCommitmentContract(
                business_id=business_id,
                job_id=job_id,
                job_proof_hash="not_built",
            ).to_dict(),
        },
        "safety": {
            "would_execute_workflow": False,
            "would_create_payment": False,
            "would_commit_to_glyphchain": False,
            "would_grant_permission": False,
            "requires_human_review": True,
        },
    }
    bundle["bundle_hash"] = stable_contract_hash("a2a_contract_bundle", bundle)
    return bundle
