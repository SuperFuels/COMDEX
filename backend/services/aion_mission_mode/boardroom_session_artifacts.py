"""
AION Phase 25K — Boardroom Session Artifact Persistence

Purpose:
- Save Boardroom/AI Council meeting packets as AION-readable business-container artifacts.
- Keep File Cabinet as an index/view, not the source of truth.
- Preserve session packet, department ledger snapshot, user context, provenance, receipt hash and replay locator.
- No live execution, no external side effects, no provider memory mutation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.aion_mission_mode.business_container_artifacts import (
    BusinessArtifactTarget,
    PilotArtifactProvenance,
    commit_pilot_artifact_to_business_container,
    validate_artifact_merkle_triad,
    validate_pilot_artifact_record,
)
from backend.services.aion_mission_mode.department_artifact_persistence import (
    business_container_id_for_business,
)
from backend.services.aion_mission_mode.department_capability_map import stable_hash


def create_boardroom_session_payload(
    *,
    business_id: str,
    session_id: str,
    session_type: str,
    business_context_packet: dict[str, Any] | None = None,
    department_intelligence_packet: dict[str, Any] | None = None,
    department_context_packet: dict[str, Any] | None = None,
    user_added_context: list[dict[str, Any]] | None = None,
    council_members: list[str] | None = None,
    previous_session_refs: list[dict[str, Any]] | None = None,
    proposed_pilot_actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "aion.boardroom_session_artifact_payload.v0",
        "business_id": str(business_id or ""),
        "session_id": str(session_id or ""),
        "session_type": str(session_type or "business_assessment"),
        "business_context_packet": business_context_packet or {},
        "department_intelligence_packet": department_intelligence_packet or {},
        "department_context_packet": department_context_packet or {},
        "user_added_context": list(user_added_context or []),
        "council_members": list(council_members or []),
        "previous_session_refs": list(previous_session_refs or []),
        "proposed_pilot_actions": list(proposed_pilot_actions or []),
        "execution_boundary": {
            "approval_gated": True,
            "pilot_waits_for_user": True,
            "live_external_side_effects_performed": False,
            "raw_model_tool_access_allowed": False,
            "provider_memory_mutation_allowed": False,
        },
    }
    payload["boardroom_session_packet_hash"] = stable_hash(
        {k: v for k, v in payload.items() if k != "boardroom_session_packet_hash"}
    )
    return payload


def commit_boardroom_session_artifact(
    *,
    business_id: str,
    session_id: str,
    session_type: str,
    business_context_packet: dict[str, Any] | None = None,
    department_intelligence_packet: dict[str, Any] | None = None,
    department_context_packet: dict[str, Any] | None = None,
    user_added_context: list[dict[str, Any]] | None = None,
    council_members: list[str] | None = None,
    previous_session_refs: list[dict[str, Any]] | None = None,
    proposed_pilot_actions: list[dict[str, Any]] | None = None,
    full_session_payload: dict[str, Any] | None = None,
    platform_root: str | Path | None = None,
) -> dict[str, Any]:
    if not business_id:
        raise ValueError("business_id_required")
    if not session_id:
        raise ValueError("session_id_required")

    target = BusinessArtifactTarget(
        business_id=business_id,
        business_container_id=business_container_id_for_business(business_id),
        sub_container="pilot",
        artifact_type="boardroom_session",
        artifact_name=f"{session_id}.json",
    )

    provenance = PilotArtifactProvenance(
        mission_id=f"boardroom_session:{session_id}",
        mission_run_id=session_id,
        step_id="boardroom_council_session_packet",
        tool_id="aion_boardroom_terminal",
        created_by="aion_pilot",
    )

    if full_session_payload is not None:
        artifact_payload = dict(full_session_payload)
        if str(artifact_payload.get("business_id") or "") != str(business_id):
            raise ValueError("boardroom_payload_business_id_mismatch")
        if str(artifact_payload.get("session_id") or "") != str(session_id):
            raise ValueError("boardroom_payload_session_id_mismatch")
        artifact_payload.setdefault("session_type", session_type)
        artifact_payload.setdefault("schema_version", "aion.boardroom_session_artifact_payload.v0")
        artifact_payload.setdefault(
            "boardroom_session_packet_hash",
            stable_hash({k: v for k, v in artifact_payload.items() if k != "boardroom_session_packet_hash"}),
        )
    else:
        artifact_payload = create_boardroom_session_payload(
            business_id=business_id,
            session_id=session_id,
            session_type=session_type,
            business_context_packet=business_context_packet,
            department_intelligence_packet=department_intelligence_packet,
            department_context_packet=department_context_packet,
            user_added_context=user_added_context,
            council_members=council_members,
            previous_session_refs=previous_session_refs,
            proposed_pilot_actions=proposed_pilot_actions,
        )

    source_payload = {
        "source": "boardroom_terminal",
        "session_id": session_id,
        "session_type": session_type,
        "business_id": business_id,
        "packet_hash": artifact_payload["boardroom_session_packet_hash"],
    }

    record = commit_pilot_artifact_to_business_container(
        target=target,
        provenance=provenance,
        artifact_payload=artifact_payload,
        source_payload=source_payload,
    )

    record["boardroom_session_state"] = "business_container_bound"
    record["file_cabinet_role"] = "index_pointer_only"
    record["replay_locator"] = {
        "business_id": business_id,
        "business_container_id": target.business_container_id,
        "sub_container": target.sub_container,
        "session_id": session_id,
        "session_type": session_type,
        "storage_path": record["storage_path"],
        "artifact_id": record["artifact_id"],
        "receipt_hash": record["receipt_hash"],
    }
    record["replay_locator_hash"] = stable_hash(record["replay_locator"])
    record["record_valid"] = validate_pilot_artifact_record(record)
    record["merkle_triad_valid"] = validate_artifact_merkle_triad(record)
    record["boardroom_session_record_hash"] = stable_hash(
        {k: v for k, v in record.items() if k != "boardroom_session_record_hash"}
    )

    if platform_root is not None:
        from backend.services.aion_mission_mode.business_container_artifacts import (
            canonical_artifact_real_path,
        )

        destination = canonical_artifact_real_path(
            platform_root=str(platform_root),
            target=target,
            artifact_id=record["artifact_id"],
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(
            json.dumps(artifact_payload, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(destination)
        record["persisted"] = True
        record["persisted_path"] = str(destination)

    return record


def create_file_cabinet_pointer_for_boardroom_session(record: dict[str, Any]) -> dict[str, Any]:
    target = record.get("target") or {}
    replay = record.get("replay_locator") or {}
    session_id = str(replay.get("session_id") or record.get("artifact_id") or "boardroom_session")

    pointer = {
        "id": f"boardroom_session_pointer_{session_id}",
        "name": f"Boardroom Session — {session_id}",
        "type": "business_container_artifact",
        "document_type": "boardroom_session",
        "target": {
            "business_container_id": target.get("business_container_id"),
            "sub_container": target.get("sub_container"),
            "artifact_type": target.get("artifact_type"),
            "storage_path": record.get("storage_path"),
            "artifact_id": record.get("artifact_id"),
            "artifact_hash": record.get("artifact_hash"),
            "receipt_hash": record.get("receipt_hash"),
            "replay_locator_hash": record.get("replay_locator_hash"),
        },
        "source_of_truth": "business_container",
        "file_cabinet_role": "index_pointer_only",
    }
    pointer["pointer_hash"] = stable_hash(pointer)
    return pointer
