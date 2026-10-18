from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json


FULFILMENT_JOB_SCHEMA_VERSION = "aion.gateway.fulfilment_job_preview.v0.1"

FULFILMENT_JOB_STATES = {
    "requested",
    "quoted",
    "accepted",
    "scheduled",
    "in_progress",
    "completed",
    "disputed",
    "failed",
}

PREVIEW_ONLY_BLOCKED_REASON = "preview_only_no_job_record_created"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_job_preview_hash(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class FulfilmentJobTimelineEvent:
    event_id: str
    event_type: str
    stage: str
    message: str
    created_at: str = field(default_factory=utc_now_iso)
    actor: str = "aion_gateway_v0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FulfilmentJobCorePreview:
    schema_version: str
    job_preview_id: str
    business_id: str
    service_type: str
    location: str
    requested_outcome: str
    lifecycle_state: str
    current_stage: str
    next_expected_event: str
    blocked_reason: str
    workflow_run_id: Optional[str] = None
    goal_id: Optional[str] = None
    job_timeline: List[Dict[str, Any]] = field(default_factory=list)
    dry_run_only: bool = True
    would_create_fulfilment_job: bool = False
    would_write_database: bool = False
    would_execute_goal_engine: bool = False
    would_write_externally: bool = False
    requires_human_review: bool = True
    job_preview_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_fulfilment_job_core_preview(
    *,
    business_id: str,
    service_type: str,
    location: str,
    requested_outcome: str,
    workflow_run_id: Optional[str] = None,
    goal_id: Optional[str] = None,
    source_intent_id: Optional[str] = None,
) -> Dict[str, Any]:
    business_id = str(business_id or "").strip()
    service_type = str(service_type or "").strip()
    location = str(location or "").strip()
    requested_outcome = str(requested_outcome or "").strip()
    source_intent_id = str(source_intent_id or "").strip()

    blocked_reasons: List[str] = []

    if not business_id:
        blocked_reasons.append("missing_business_id")
    if not service_type:
        blocked_reasons.append("missing_service_type")
    if not requested_outcome:
        blocked_reasons.append("missing_requested_outcome")

    blocked_reasons.append(PREVIEW_ONLY_BLOCKED_REASON)

    seed = {
        "schema_version": FULFILMENT_JOB_SCHEMA_VERSION,
        "business_id": business_id.lower(),
        "service_type": service_type.lower(),
        "location": location.lower(),
        "requested_outcome": requested_outcome,
        "source_intent_id": source_intent_id,
    }
    preview_hash = stable_job_preview_hash(seed)
    job_preview_id = f"job_preview_{preview_hash[:16]}"

    timeline = [
        FulfilmentJobTimelineEvent(
            event_id=f"evt_{preview_hash[:12]}",
            event_type="fulfilment_job_preview_created",
            stage="requested",
            message="Preview-only fulfilment job created from normalized inbound intent.",
            metadata={
                "source_intent_id": source_intent_id,
                "dry_run_only": True,
                "would_create_fulfilment_job": False,
            },
        ).to_dict()
    ]

    preview = FulfilmentJobCorePreview(
        schema_version=FULFILMENT_JOB_SCHEMA_VERSION,
        job_preview_id=job_preview_id,
        business_id=business_id,
        service_type=service_type,
        location=location,
        requested_outcome=requested_outcome,
        lifecycle_state="requested",
        current_stage="requested",
        next_expected_event="human_review",
        blocked_reason=",".join(blocked_reasons),
        workflow_run_id=workflow_run_id,
        goal_id=goal_id,
        job_timeline=timeline,
        job_preview_hash=preview_hash,
        metadata={
            "source_intent_id": source_intent_id,
            "allowed_lifecycle_states": sorted(FULFILMENT_JOB_STATES),
            "blocked_reasons": blocked_reasons,
            "preview_only": True,
            "no_database_write": True,
            "no_public_route": True,
        },
    )

    return preview.to_dict()
