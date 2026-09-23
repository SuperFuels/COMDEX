"""
AION Phase 20N.3 — Human Task Cards + Evidence Binding

Locks:
- Human-required work is a first-class mission pause, not failure.
- Human task cards define instructions, evidence, resume conditions and hashes.
- Missing evidence prevents resume.
- Valid evidence can resume mission.
- Evidence records are hash-bound and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any, Literal


HumanTaskStatus = Literal[
    "waiting_human_task",
    "evidence_submitted",
    "evidence_validated",
    "evidence_rejected",
    "completed",
]

EvidenceType = Literal[
    "url",
    "screenshot_hash",
    "confirmation_code",
    "uploaded_file_hash",
    "manual_attestation",
    "provider_callback",
]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HumanTaskCard:
    schema_version: str
    human_task_id: str
    mission_id: str
    mission_run_id: str
    step_id: str
    title: str
    reason: str
    instructions: list[str]
    required_evidence_type: EvidenceType
    required_evidence_fields: list[str]
    blocking_status: bool
    resume_condition: str
    status: HumanTaskStatus
    provider: str | None
    task_hash: str


def create_human_task_card(
    *,
    mission_id: str,
    mission_run_id: str,
    step_id: str,
    title: str,
    reason: str,
    instructions: list[str],
    required_evidence_type: EvidenceType,
    required_evidence_fields: list[str],
    provider: str | None = None,
) -> dict[str, Any]:
    card = {
        "schema_version": "aion.human_task_card.v0",
        "human_task_id": f"human_task::{mission_id}::{mission_run_id}::{step_id}",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "step_id": step_id,
        "title": title,
        "reason": reason,
        "instructions": instructions,
        "required_evidence_type": required_evidence_type,
        "required_evidence_fields": required_evidence_fields,
        "blocking_status": True,
        "resume_condition": "required_evidence_validated",
        "status": "waiting_human_task",
        "provider": provider,
        "task_hash": "",
    }
    card["task_hash"] = _hash({k: v for k, v in card.items() if k != "task_hash"})
    return card


def create_facebook_page_human_task(
    *,
    mission_id: str,
    mission_run_id: str,
    step_id: str = "facebook_page",
    business_name: str = "Home Fixed",
) -> dict[str, Any]:
    return create_human_task_card(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        step_id=step_id,
        title="Create or connect Facebook Business Page",
        reason="Facebook requires real account ownership and may require identity or phone verification.",
        instructions=[
            "Log in to Facebook using the real business owner account.",
            f"Create or connect the business page for {business_name}.",
            "Add phone number, service area and business category.",
            "Return to AION and submit the Facebook Page URL as evidence.",
        ],
        required_evidence_type="url",
        required_evidence_fields=["page_url"],
        provider="Meta",
    )


def create_phone_verification_human_task(
    *,
    mission_id: str,
    mission_run_id: str,
    step_id: str = "phone_verification",
    provider: str = "provider",
) -> dict[str, Any]:
    return create_human_task_card(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        step_id=step_id,
        title="Complete phone verification",
        reason="The provider requires a real phone verification step that AION Pilot must not complete autonomously.",
        instructions=[
            "Open the provider verification screen.",
            "Complete the phone verification challenge.",
            "Return to AION and submit the confirmation code or confirmation text.",
        ],
        required_evidence_type="confirmation_code",
        required_evidence_fields=["confirmation_code"],
        provider=provider,
    )


def submit_human_task_evidence(
    *,
    task_card: dict[str, Any],
    submitted_by: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    record = {
        "schema_version": "aion.human_task_evidence.v0",
        "human_task_id": task_card["human_task_id"],
        "mission_id": task_card["mission_id"],
        "mission_run_id": task_card["mission_run_id"],
        "step_id": task_card["step_id"],
        "submitted_by": submitted_by,
        "required_evidence_type": task_card["required_evidence_type"],
        "required_evidence_fields": task_card["required_evidence_fields"],
        "evidence": evidence,
        "evidence_hash": "",
    }
    record["evidence_hash"] = _hash({k: v for k, v in record.items() if k != "evidence_hash"})
    return record


def validate_human_task_evidence(
    *,
    task_card: dict[str, Any],
    evidence_record: dict[str, Any] | None,
) -> dict[str, Any]:
    missing_fields: list[str] = []

    if evidence_record is None:
        missing_fields = list(task_card["required_evidence_fields"])
        valid = False
        reason = "missing_evidence"
    else:
        evidence = evidence_record.get("evidence", {})
        for field in task_card["required_evidence_fields"]:
            value = evidence.get(field)
            if value is None or value == "":
                missing_fields.append(field)

        valid = not missing_fields
        reason = "evidence_validated" if valid else "missing_required_evidence_fields"

    result = {
        "schema_version": "aion.human_task_evidence_validation.v0",
        "human_task_id": task_card["human_task_id"],
        "mission_id": task_card["mission_id"],
        "mission_run_id": task_card["mission_run_id"],
        "step_id": task_card["step_id"],
        "task_hash": task_card["task_hash"],
        "evidence_hash": evidence_record.get("evidence_hash") if evidence_record else None,
        "valid": valid,
        "missing_fields": missing_fields,
        "resume_allowed": valid,
        "mission_state": "running_autonomous_steps" if valid else "waiting_human_task",
        "reason": reason,
        "validation_hash": "",
    }
    result["validation_hash"] = _hash({k: v for k, v in result.items() if k != "validation_hash"})
    return result


def complete_human_task(
    *,
    task_card: dict[str, Any],
    evidence_record: dict[str, Any],
    completed_by: str,
) -> dict[str, Any]:
    validation = validate_human_task_evidence(
        task_card=task_card,
        evidence_record=evidence_record,
    )

    completed = validation["valid"]

    result = {
        "schema_version": "aion.human_task_completion.v0",
        "human_task_id": task_card["human_task_id"],
        "mission_id": task_card["mission_id"],
        "mission_run_id": task_card["mission_run_id"],
        "step_id": task_card["step_id"],
        "completed_by": completed_by,
        "completed": completed,
        "status": "completed" if completed else "evidence_rejected",
        "resume_allowed": completed,
        "mission_state": "running_autonomous_steps" if completed else "waiting_human_task",
        "task_hash": task_card["task_hash"],
        "evidence_hash": evidence_record["evidence_hash"],
        "validation_hash": validation["validation_hash"],
        "completion_hash": "",
    }
    result["completion_hash"] = _hash({k: v for k, v in result.items() if k != "completion_hash"})
    return result


def human_task_from_plan_step(
    *,
    mission_id: str,
    mission_run_id: str,
    step: dict[str, Any],
) -> dict[str, Any]:
    action_type = step.get("action_type", "")

    if action_type == "create_real_facebook_account":
        return create_facebook_page_human_task(
            mission_id=mission_id,
            mission_run_id=mission_run_id,
            step_id=step["step_id"],
            business_name=step.get("business_name", "Home Fixed"),
        )

    if action_type == "verify_phone_number":
        return create_phone_verification_human_task(
            mission_id=mission_id,
            mission_run_id=mission_run_id,
            step_id=step["step_id"],
            provider=step.get("provider", "provider"),
        )

    return create_human_task_card(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        step_id=step["step_id"],
        title=step.get("title", "Human task required"),
        reason=step.get("reason", "This step requires direct human action."),
        instructions=step.get("instructions", ["Complete the required human action and return to AION."]),
        required_evidence_type=step.get("required_evidence_type", "manual_attestation"),
        required_evidence_fields=step.get("required_evidence_fields", ["attestation"]),
        provider=step.get("provider"),
    )
