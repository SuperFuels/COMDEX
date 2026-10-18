"""
AION Phase 20AA — Business Container Artifact Persistence

Contract:
- AION Pilot-created end-user artifacts must be saved inside the active business container.
- Session VFS drafts are temporary only.
- Promoted artifacts require business_id, business_container_id, sub_container, hashes, provenance, and receipt metadata.
- Pilot cannot save user-usable files globally or outside business container hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ALLOWED_BUSINESS_SUB_CONTAINERS = {
    "missions",
    "campaigns",
    "quotes",
    "workflows",
    "agentmaps",
    "reports",
    "evidence",
    "exports",
    "approvals",
    "receipts",
    "marketing",
    "pilot",
    "sales",
    "finance",
    "operations",
    "support",
    "builder",
}


USER_USABLE_ARTIFACT_TYPES = {
    "pdf",
    "spreadsheet",
    "document",
    "text",
    "markdown",
    "json",
    "campaign_pack",
    "campaign_offer",
    "advert_draft",
    "landing_page_copy",
    "quote_preview",
    "workflow_preview",
    "agentmap_preview",
    "report",
    "approval_payload",
    "mission_receipt",
    "evidence_bundle",
    "export",
    "boardroom_session",
}


@dataclass(frozen=True)
class BusinessArtifactTarget:
    business_id: str
    business_container_id: str
    sub_container: str
    artifact_type: str
    artifact_name: str


@dataclass(frozen=True)
class PilotArtifactProvenance:
    mission_id: str
    mission_run_id: str
    step_id: str
    tool_id: str
    created_by: str = "aion_pilot"


@dataclass(frozen=True)
class BusinessContainerArtifactRecord:
    artifact_id: str
    target: dict[str, Any]
    provenance: dict[str, Any]
    artifact_payload: dict[str, Any]
    artifact_hash: str
    source_payload_hash: str
    receipt_hash: str
    storage_state: str = "committed_to_business_container"
    session_vfs_only: bool = False
    live_side_effects_enabled: bool = False


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def is_allowed_sub_container(sub_container: str) -> bool:
    return str(sub_container or "") in ALLOWED_BUSINESS_SUB_CONTAINERS


def is_user_usable_artifact_type(artifact_type: str) -> bool:
    return str(artifact_type or "") in USER_USABLE_ARTIFACT_TYPES


def build_artifact_id(
    *,
    business_id: str,
    mission_id: str,
    step_id: str,
    artifact_type: str,
) -> str:
    return "artifact_" + _hash(
        {
            "business_id": business_id,
            "mission_id": mission_id,
            "step_id": step_id,
            "artifact_type": artifact_type,
        }
    )[:24]


def validate_artifact_target(target: BusinessArtifactTarget) -> None:
    if not target.business_id:
        raise ValueError("business_id_required")

    if not target.business_container_id:
        raise ValueError("business_container_id_required")

    if not is_allowed_sub_container(target.sub_container):
        raise ValueError(f"invalid_business_sub_container:{target.sub_container}")

    if not is_user_usable_artifact_type(target.artifact_type):
        raise ValueError(f"invalid_user_usable_artifact_type:{target.artifact_type}")

    if target.business_container_id in {"global", "root", "session_vfs", "tmp", "temp"}:
        raise ValueError("artifact_target_must_be_active_business_container")


def business_container_path(target: BusinessArtifactTarget, artifact_id: str) -> str:
    validate_artifact_target(target)
    return (
        f"business_containers/{target.business_container_id}/"
        f"{target.sub_container}/{artifact_id}.json"
    )


def commit_pilot_artifact_to_business_container(
    *,
    target: BusinessArtifactTarget,
    provenance: PilotArtifactProvenance,
    artifact_payload: dict[str, Any],
    source_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_artifact_target(target)

    if provenance.created_by != "aion_pilot":
        raise ValueError("created_by_must_be_aion_pilot")

    artifact_id = build_artifact_id(
        business_id=target.business_id,
        mission_id=provenance.mission_id,
        step_id=provenance.step_id,
        artifact_type=target.artifact_type,
    )

    artifact_hash = _hash(artifact_payload)
    source_payload_hash = _hash(source_payload or artifact_payload)

    receipt_payload = {
        "artifact_id": artifact_id,
        "target": asdict(target),
        "provenance": asdict(provenance),
        "artifact_hash": artifact_hash,
        "source_payload_hash": source_payload_hash,
        "storage_path": business_container_path(target, artifact_id),
    }

    receipt_hash = artifact_merkle_triad_hash(
        artifact_hash=artifact_hash,
        source_payload_hash=source_payload_hash,
        provenance=asdict(provenance),
        storage_path=business_container_path(target, artifact_id),
    )

    record = BusinessContainerArtifactRecord(
        artifact_id=artifact_id,
        target=asdict(target),
        provenance=asdict(provenance),
        artifact_payload=dict(artifact_payload),
        artifact_hash=artifact_hash,
        source_payload_hash=source_payload_hash,
        receipt_hash=receipt_hash,
    )

    data = asdict(record)
    data["storage_path"] = business_container_path(target, artifact_id)
    return data


def validate_pilot_artifact_record(record: dict[str, Any]) -> bool:
    target = record.get("target") or {}
    provenance = record.get("provenance") or {}

    if record.get("session_vfs_only") is True:
        return False

    if record.get("storage_state") != "committed_to_business_container":
        return False

    if record.get("live_side_effects_enabled") is True:
        return False

    if provenance.get("created_by") != "aion_pilot":
        return False

    if not target.get("business_id") or not target.get("business_container_id"):
        return False

    if not is_allowed_sub_container(target.get("sub_container", "")):
        return False

    if not is_user_usable_artifact_type(target.get("artifact_type", "")):
        return False

    storage_path = str(record.get("storage_path") or "")
    required_prefix = f"business_containers/{target['business_container_id']}/{target['sub_container']}/"

    if not storage_path.startswith(required_prefix):
        return False

    return all(
        record.get(key)
        for key in [
            "artifact_id",
            "artifact_hash",
            "source_payload_hash",
            "receipt_hash",
        ]
    )


class ArtifactPathContainmentError(ValueError):
    """Raised when an artifact target attempts to escape its business container."""


def canonical_business_container_root(*, platform_root: str, business_container_id: str) -> Path:
    if business_container_id in {"", "global", "root", "session_vfs", "tmp", "temp"}:
        raise ArtifactPathContainmentError("invalid_business_container_root")

    root = Path(platform_root).resolve()
    return (root / "business_containers" / business_container_id).resolve()


def canonical_artifact_real_path(
    *,
    platform_root: str,
    target: BusinessArtifactTarget,
    artifact_id: str,
) -> Path:
    validate_artifact_target(target)

    active_business_root = canonical_business_container_root(
        platform_root=platform_root,
        business_container_id=target.business_container_id,
    )

    destination = (
        active_business_root /
        target.sub_container /
        f"{artifact_id}.json"
    ).resolve()

    try:
        destination.relative_to(active_business_root)
    except ValueError as exc:
        raise ArtifactPathContainmentError(
            f"artifact_path_escape:{destination}"
        ) from exc

    return destination


def validate_canonical_path_containment(
    *,
    platform_root: str,
    target: BusinessArtifactTarget,
    artifact_id: str,
) -> bool:
    canonical_artifact_real_path(
        platform_root=platform_root,
        target=target,
        artifact_id=artifact_id,
    )
    return True


def artifact_merkle_triad_hash(
    *,
    artifact_hash: str,
    source_payload_hash: str,
    provenance: dict[str, Any],
    storage_path: str,
) -> str:
    return sha256(
        (
            str(artifact_hash) +
            str(source_payload_hash) +
            _canonical_json(provenance) +
            str(storage_path)
        ).encode("utf-8")
    ).hexdigest()


def validate_artifact_merkle_triad(record: dict[str, Any]) -> bool:
    expected = artifact_merkle_triad_hash(
        artifact_hash=str(record.get("artifact_hash") or ""),
        source_payload_hash=str(record.get("source_payload_hash") or ""),
        provenance=dict(record.get("provenance") or {}),
        storage_path=str(record.get("storage_path") or ""),
    )
    return expected == record.get("receipt_hash")
