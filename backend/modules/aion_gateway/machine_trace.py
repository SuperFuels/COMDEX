from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import hashlib
import json
from datetime import datetime, timezone


A2A_TRACE_SCHEMA_VERSION = "aion.a2a.trace.v0.1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class MachineA2ATrace:
    schema_version: str = A2A_TRACE_SCHEMA_VERSION
    trace_type: str = "aion_machine_a2a_trace"

    job_id: str = ""
    business_id: str = ""
    workflow_run_id: Optional[str] = None
    goal_id: Optional[str] = None

    current_stage: str = "requested"
    next_expected_event: str = "human_review"
    blocked_reason: str = ""

    provider_assignment: Dict[str, Any] = field(default_factory=dict)
    eta: Dict[str, Any] = field(default_factory=dict)

    evidence_state: Dict[str, Any] = field(default_factory=dict)
    approval_state: Dict[str, Any] = field(default_factory=dict)
    exception_state: Dict[str, Any] = field(default_factory=dict)
    settlement_readiness_state: Dict[str, Any] = field(default_factory=dict)
    proof_commitment_state: Dict[str, Any] = field(default_factory=dict)

    dry_run_only: bool = True
    would_execute_goal_engine: bool = False
    would_write_externally: bool = False
    would_mutate_business_state: bool = False
    would_grant_permission: bool = False

    human_boardroom_alignment: Dict[str, Any] = field(default_factory=dict)
    machine_trace_hash: str = ""
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data.get("machine_trace_hash"):
            hash_payload = dict(data)
            hash_payload.pop("machine_trace_hash", None)
            hash_payload.pop("created_at", None)
            data["machine_trace_hash"] = _stable_hash(hash_payload)
        return data


def build_machine_a2a_trace(
    *,
    fulfilment_job: Dict[str, Any],
    evidence_state: Optional[Dict[str, Any]] = None,
    approval_state: Optional[Dict[str, Any]] = None,
    exception_state: Optional[Dict[str, Any]] = None,
    settlement_readiness_state: Optional[Dict[str, Any]] = None,
    proof_commitment_state: Optional[Dict[str, Any]] = None,
    provider_assignment: Optional[Dict[str, Any]] = None,
    eta: Optional[Dict[str, Any]] = None,
    human_boardroom_alignment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    job = dict(fulfilment_job or {})

    trace = MachineA2ATrace(
        job_id=str(job.get("job_id") or ""),
        business_id=str(job.get("business_id") or ""),
        workflow_run_id=job.get("workflow_run_id"),
        goal_id=job.get("goal_id"),
        current_stage=str(job.get("current_stage") or job.get("status") or "requested"),
        next_expected_event=str(job.get("next_expected_event") or "human_review"),
        blocked_reason=str(job.get("blocked_reason") or ""),
        provider_assignment=dict(provider_assignment or {}),
        eta=dict(eta or {}),
        evidence_state=dict(evidence_state or {}),
        approval_state=dict(approval_state or {}),
        exception_state=dict(exception_state or {}),
        settlement_readiness_state=dict(settlement_readiness_state or {}),
        proof_commitment_state=dict(proof_commitment_state or {}),
        dry_run_only=True,
        would_execute_goal_engine=False,
        would_write_externally=False,
        would_mutate_business_state=False,
        would_grant_permission=False,
        human_boardroom_alignment=dict(human_boardroom_alignment or {}),
    )

    return trace.to_dict()
