from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json


FULFILMENT_JOB_SCHEMA_VERSION = "aion.fulfilment_job.v0.1"

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

TERMINAL_FULFILMENT_JOB_STATES = {
    "completed",
    "disputed",
    "failed",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_job_id(
    *,
    business_id: str,
    service_type: str,
    location: str,
    requested_outcome: str,
    created_at: str,
) -> str:
    payload = {
        "schema_version": FULFILMENT_JOB_SCHEMA_VERSION,
        "business_id": str(business_id or "").lower(),
        "service_type": str(service_type or "").lower(),
        "location": str(location or "").lower(),
        "requested_outcome": str(requested_outcome or ""),
        "created_at": str(created_at or ""),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "job_" + hashlib.sha256(encoded).hexdigest()[:24]


@dataclass(frozen=True)
class FulfilmentJobTimelineEvent:
    event_id: str
    event_type: str
    stage: str
    message: str
    created_at: str
    actor: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FulfilmentJob:
    schema_version: str
    job_id: str
    business_id: str
    service_type: str
    location: str
    requested_outcome: str
    lifecycle_state: str
    current_stage: str
    next_expected_event: str
    blocked_reason: str = ""
    workflow_run_id: Optional[str] = None
    goal_id: Optional[str] = None
    job_timeline: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def make_timeline_event(
    *,
    job_id: str,
    event_type: str,
    stage: str,
    message: str,
    actor: str = "system",
    created_at: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    created_at = created_at or utc_now_iso()
    seed = {
        "job_id": job_id,
        "event_type": event_type,
        "stage": stage,
        "message": message,
        "actor": actor,
        "created_at": created_at,
    }
    encoded = json.dumps(seed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    event_id = "job_event_" + hashlib.sha256(encoded).hexdigest()[:24]

    return FulfilmentJobTimelineEvent(
        event_id=event_id,
        event_type=str(event_type or ""),
        stage=str(stage or ""),
        message=str(message or ""),
        actor=str(actor or "system"),
        created_at=created_at,
        metadata=dict(metadata or {}),
    ).to_dict()


def create_fulfilment_job(
    *,
    business_id: str,
    service_type: str,
    location: str,
    requested_outcome: str,
    workflow_run_id: Optional[str] = None,
    goal_id: Optional[str] = None,
    created_at: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    created_at = created_at or utc_now_iso()

    business_id = str(business_id or "").strip()
    service_type = str(service_type or "").strip()
    location = str(location or "").strip()
    requested_outcome = str(requested_outcome or "").strip()

    blocked_reasons = []
    if not business_id:
        blocked_reasons.append("missing_business_id")
    if not service_type:
        blocked_reasons.append("missing_service_type")
    if not location:
        blocked_reasons.append("missing_location")
    if not requested_outcome:
        blocked_reasons.append("missing_requested_outcome")

    lifecycle_state = "failed" if blocked_reasons else "requested"
    blocked_reason = ",".join(blocked_reasons)

    job_id = stable_job_id(
        business_id=business_id,
        service_type=service_type,
        location=location,
        requested_outcome=requested_outcome,
        created_at=created_at,
    )

    timeline = [
        make_timeline_event(
            job_id=job_id,
            event_type="job_created" if not blocked_reasons else "job_blocked",
            stage=lifecycle_state,
            message="Fulfilment job created." if not blocked_reasons else "Fulfilment job blocked by missing required fields.",
            created_at=created_at,
            metadata={"blocked_reasons": blocked_reasons},
        )
    ]

    job = FulfilmentJob(
        schema_version=FULFILMENT_JOB_SCHEMA_VERSION,
        job_id=job_id,
        business_id=business_id,
        service_type=service_type,
        location=location,
        requested_outcome=requested_outcome,
        lifecycle_state=lifecycle_state,
        current_stage=lifecycle_state,
        next_expected_event="quote_required" if not blocked_reasons else "human_review_required",
        blocked_reason=blocked_reason,
        workflow_run_id=workflow_run_id,
        goal_id=goal_id,
        job_timeline=timeline,
        created_at=created_at,
        updated_at=created_at,
        metadata=dict(metadata or {}),
    )

    return job.to_dict()


def append_fulfilment_job_timeline_event(
    job: Dict[str, Any],
    *,
    event_type: str,
    stage: str,
    message: str,
    actor: str = "system",
    metadata: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(job, dict):
        raise TypeError("job must be a dict")

    next_job = dict(job)
    timeline = list(next_job.get("job_timeline") or [])

    event = make_timeline_event(
        job_id=str(next_job.get("job_id") or ""),
        event_type=event_type,
        stage=stage,
        message=message,
        actor=actor,
        created_at=created_at,
        metadata=metadata,
    )

    timeline.append(event)

    next_job["job_timeline"] = timeline
    next_job["current_stage"] = str(stage or next_job.get("current_stage") or "")
    next_job["lifecycle_state"] = str(stage or next_job.get("lifecycle_state") or "")
    next_job["updated_at"] = event["created_at"]

    if next_job["lifecycle_state"] in TERMINAL_FULFILMENT_JOB_STATES:
        next_job["next_expected_event"] = "none"
    else:
        next_job["next_expected_event"] = str((metadata or {}).get("next_expected_event") or next_job.get("next_expected_event") or "")

    return next_job
