"""
AION Phase 23V — Department Artifact Persistence

Purpose:
- Bind Pilot-created artifacts to the correct business + department container.
- Preserve mission/run/business/department/tool provenance.
- Produce deterministic storage path, receipt hash and replay locator.
- Do not permit global/session/temp artifact targets.
"""

from __future__ import annotations

from typing import Any

from backend.services.aion_mission_mode.business_container_artifacts import (
    BusinessArtifactTarget,
    PilotArtifactProvenance,
    commit_pilot_artifact_to_business_container,
    validate_artifact_merkle_triad,
    validate_pilot_artifact_record,
)
from backend.services.aion_mission_mode.department_capability_map import (
    is_supported_department,
    normalize_department_id,
    stable_hash,
)


def business_container_id_for_business(business_id: str) -> str:
    raw_value = str(business_id or "").strip().lower()
    value = raw_value.replace("_", "-")

    if not value:
        raise ValueError("business_id_required")

    blocked_values = {
        "global",
        "root",
        "session_vfs",
        "session-vfs",
        "tmp",
        "temp",
    }

    if raw_value in blocked_values or value in blocked_values:
        raise ValueError("invalid_business_container_id")

    return value


def artifact_type_for_tool_execution_item(tool_execution_item: dict[str, Any]) -> str:
    artifact_type = str(tool_execution_item.get("artifact_type") or "document").strip()
    if artifact_type in {"markdown", "text", "json", "pdf", "spreadsheet", "document"}:
        return artifact_type
    if artifact_type in {"campaign_pack", "advert_draft", "landing_page_copy", "report"}:
        return artifact_type
    return "document"


def department_artifact_name(*, tool_execution_item: dict[str, Any], artifact_card: dict[str, Any] | None = None) -> str:
    if artifact_card and artifact_card.get("artifact_name"):
        return str(artifact_card["artifact_name"])

    task_id = str(tool_execution_item.get("task_id") or "department_task").strip()
    capability = str(tool_execution_item.get("department_capability") or "artifact").replace(".", "_")
    return f"{task_id}_{capability}.json"


def commit_department_artifact_from_pilot_result(
    *,
    pilot_result: dict[str, Any],
    tool_execution_item: dict[str, Any],
) -> dict[str, Any]:
    business_id = str(
        pilot_result.get("business_id")
        or tool_execution_item.get("business_id")
        or ""
    )
    mission_id = str(
        pilot_result.get("mission_id")
        or tool_execution_item.get("mission_id")
        or ""
    )
    mission_run_id = str(
        pilot_result.get("mission_run_id")
        or tool_execution_item.get("mission_run_id")
        or ""
    )
    step_id = str(
        pilot_result.get("step_id")
        or tool_execution_item.get("task_id")
        or ""
    )
    department_id = normalize_department_id(
        pilot_result.get("department_id")
        or tool_execution_item.get("department_id")
        or ""
    )

    if not is_supported_department(department_id):
        raise ValueError(f"unsupported_department_id:{department_id}")

    artifact_card = pilot_result.get("artifact_card") if isinstance(pilot_result.get("artifact_card"), dict) else {}

    target = BusinessArtifactTarget(
        business_id=business_id,
        business_container_id=business_container_id_for_business(business_id),
        sub_container=department_id,
        artifact_type=artifact_type_for_tool_execution_item(tool_execution_item),
        artifact_name=department_artifact_name(
            tool_execution_item=tool_execution_item,
            artifact_card=artifact_card,
        ),
    )

    provenance = PilotArtifactProvenance(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        step_id=step_id,
        tool_id=str(tool_execution_item.get("local_tool_id") or tool_execution_item.get("gateway_tool_name") or "aion_pilot"),
        created_by="aion_pilot",
    )

    artifact_payload = {
        "schema_version": "aion.department_artifact_payload.v0",
        "business_id": business_id,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "department_id": department_id,
        "department_display_name": tool_execution_item.get("department_display_name"),
        "department_capability": tool_execution_item.get("department_capability"),
        "task_id": tool_execution_item.get("task_id"),
        "tool_execution_item_hash": tool_execution_item.get("tool_execution_item_hash"),
        "artifact_card": artifact_card,
        "artifact_hash": pilot_result.get("artifact_hash") or artifact_card.get("artifact_hash"),
        "receipt_hash": pilot_result.get("receipt_hash") or artifact_card.get("artifact_receipt_hash"),
        "output_text": pilot_result.get("output_text"),
        "live_external_side_effects_performed": False,
        "raw_tool_execution_allowed": False,
    }

    source_payload = {
        "pilot_result_hash": pilot_result.get("execution_hash"),
        "tool_execution_item_hash": tool_execution_item.get("tool_execution_item_hash"),
        "department_id": department_id,
        "department_capability": tool_execution_item.get("department_capability"),
    }

    record = commit_pilot_artifact_to_business_container(
        target=target,
        provenance=provenance,
        artifact_payload=artifact_payload,
        source_payload=source_payload,
    )

    record["department_id"] = department_id
    record["department_artifact_state"] = "department_container_bound"
    record["replay_locator"] = {
        "business_id": business_id,
        "business_container_id": target.business_container_id,
        "department_id": department_id,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "step_id": step_id,
        "storage_path": record["storage_path"],
        "artifact_id": record["artifact_id"],
        "receipt_hash": record["receipt_hash"],
    }
    record["replay_locator_hash"] = stable_hash(record["replay_locator"])
    record["record_valid"] = validate_pilot_artifact_record(record)
    record["merkle_triad_valid"] = validate_artifact_merkle_triad(record)
    record["department_artifact_record_hash"] = stable_hash(
        {k: v for k, v in record.items() if k != "department_artifact_record_hash"}
    )
    return record


def summarize_department_artifact_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda item: item.get("department_artifact_record_hash", ""))
    summary = {
        "schema_version": "aion.department_artifact_record_summary.v0",
        "record_count": len(ordered),
        "department_ids": sorted({str(item.get("department_id") or "") for item in ordered}),
        "record_hashes": [item.get("department_artifact_record_hash") for item in ordered],
        "receipt_hashes": [item.get("receipt_hash") for item in ordered],
        "all_records_valid": all(item.get("record_valid") is True for item in ordered),
        "all_merkle_triads_valid": all(item.get("merkle_triad_valid") is True for item in ordered),
        "live_external_side_effects_enabled": False,
        "summary_hash": "",
    }
    summary["summary_hash"] = stable_hash({k: v for k, v in summary.items() if k != "summary_hash"})
    return summary
