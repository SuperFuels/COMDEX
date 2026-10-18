"""
AION Phase 20X — Session VFS + Workspace Isolation

Contract:
- Every mission run gets an isolated Session VFS.
- Temp paths, draft outputs and vector workspace IDs are salted with mission_hash.
- Cross-mission transient reads/writes are blocked by default.
- Session VFS contains no live secrets or production credentials.
- Cross-mission transfer requires governed approval.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ALLOWED_SESSION_SUBSPACES = {
    "drafts",
    "tmp",
    "vectors",
    "repair",
    "previews",
    "logs",
    "receipts",
}

FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "secret",
    "password",
    "token",
    "private_key",
    "prod_database_url",
    "production_credentials",
    "stripe_secret",
    "revolut_secret",
    "openai_api_key",
}


@dataclass(frozen=True)
class SessionVFSContext:
    mission_id: str
    mission_run_id: str
    business_id: str
    mission_hash: str
    workspace_root: str = "session_vfs"


@dataclass(frozen=True)
class SessionVFSPath:
    mission_id: str
    mission_run_id: str
    subspace: str
    name: str
    relative_path: str
    path_hash: str


@dataclass(frozen=True)
class CrossMissionTransferApproval:
    source_mission_id: str
    target_mission_id: str
    approved_by: str
    reason: str
    approved: bool
    approval_hash: str = ""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _slug(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def session_namespace(ctx: SessionVFSContext) -> str:
    return _hash(
        {
            "mission_id": ctx.mission_id,
            "mission_run_id": ctx.mission_run_id,
            "business_id": ctx.business_id,
            "mission_hash": ctx.mission_hash,
        }
    )[7:31]


def vector_workspace_id(ctx: SessionVFSContext) -> str:
    return "vector_" + session_namespace(ctx)


def validate_subspace(subspace: str) -> None:
    if _slug(subspace) not in ALLOWED_SESSION_SUBSPACES:
        raise ValueError(f"invalid_session_subspace:{subspace}")


def validate_no_live_secrets(payload: dict[str, Any]) -> bool:
    def scan(value: Any) -> bool:
        if isinstance(value, dict):
            for key, item in value.items():
                if _slug(key) in FORBIDDEN_SECRET_KEYS:
                    return False
                if scan(item) is False:
                    return False
        elif isinstance(value, list):
            for item in value:
                if scan(item) is False:
                    return False
        return True

    return scan(payload)


def session_vfs_path(
    *,
    ctx: SessionVFSContext,
    subspace: str,
    name: str,
) -> dict[str, Any]:
    validate_subspace(subspace)

    safe_subspace = _slug(subspace)
    safe_name = _slug(name)

    if not safe_name:
        raise ValueError("session_vfs_name_required")

    namespace = session_namespace(ctx)
    relative_path = (
        f"{ctx.workspace_root}/"
        f"{ctx.business_id}/"
        f"{ctx.mission_id}/"
        f"{ctx.mission_run_id}/"
        f"{namespace}/"
        f"{safe_subspace}/"
        f"{safe_name}.json"
    )

    data = SessionVFSPath(
        mission_id=ctx.mission_id,
        mission_run_id=ctx.mission_run_id,
        subspace=safe_subspace,
        name=safe_name,
        relative_path=relative_path,
        path_hash=_hash(relative_path),
    )
    return asdict(data)


def assert_same_mission_scope(*, ctx: SessionVFSContext, path_record: dict[str, Any]) -> bool:
    return (
        path_record.get("mission_id") == ctx.mission_id
        and path_record.get("mission_run_id") == ctx.mission_run_id
        and f"/{ctx.mission_id}/{ctx.mission_run_id}/" in path_record.get("relative_path", "")
    )


def write_session_vfs_record(
    *,
    ctx: SessionVFSContext,
    subspace: str,
    name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not validate_no_live_secrets(payload):
        raise ValueError("session_vfs_payload_contains_live_secret")

    path = session_vfs_path(ctx=ctx, subspace=subspace, name=name)

    record = {
        "storage_state": "session_vfs_draft",
        "session_vfs_only": True,
        "business_id": ctx.business_id,
        "mission_id": ctx.mission_id,
        "mission_run_id": ctx.mission_run_id,
        "mission_hash": ctx.mission_hash,
        "vector_workspace_id": vector_workspace_id(ctx),
        "path": path,
        "payload": dict(payload),
        "record_hash": "",
    }
    record["record_hash"] = _hash(record)
    return record


def can_read_session_vfs_record(*, ctx: SessionVFSContext, record: dict[str, Any]) -> bool:
    path = record.get("path") or {}
    return (
        record.get("mission_id") == ctx.mission_id
        and record.get("mission_run_id") == ctx.mission_run_id
        and record.get("mission_hash") == ctx.mission_hash
        and assert_same_mission_scope(ctx=ctx, path_record=path)
    )


def build_cross_mission_transfer_approval(
    *,
    source_mission_id: str,
    target_mission_id: str,
    approved_by: str,
    reason: str,
    approved: bool,
) -> dict[str, Any]:
    payload = {
        "source_mission_id": source_mission_id,
        "target_mission_id": target_mission_id,
        "approved_by": approved_by,
        "reason": reason,
        "approved": approved,
    }
    payload["approval_hash"] = _hash(payload)
    return payload


def can_transfer_between_missions(
    *,
    source_record: dict[str, Any],
    target_ctx: SessionVFSContext,
    approval: dict[str, Any] | None = None,
) -> bool:
    if source_record.get("mission_id") == target_ctx.mission_id:
        return True

    if not approval:
        return False

    return (
        approval.get("approved") is True
        and approval.get("source_mission_id") == source_record.get("mission_id")
        and approval.get("target_mission_id") == target_ctx.mission_id
        and bool(approval.get("approval_hash"))
    )


class SessionVFSPolicyViolation(RuntimeError):
    """Raised when Session VFS path containment or transfer authorization fails."""


def mission_vfs_boundary_path(*, ctx: SessionVFSContext, base_root: str = ".") -> str:
    """
    Absolute mission-scoped VFS boundary.

    All real filesystem reads/writes for this mission must remain under:
    <base_root>/session_vfs/<business_id>/<mission_id>/<mission_run_id>/
    """
    root = Path(base_root).resolve()
    return str(
        (
            root
            / ctx.workspace_root
            / _slug(ctx.business_id)
            / _slug(ctx.mission_id)
            / _slug(ctx.mission_run_id)
        ).resolve()
    )


def assert_vfs_real_path_contained(
    *,
    ctx: SessionVFSContext,
    candidate_path: str,
    base_root: str = ".",
    symlink_detected: bool = False,
    hardlink_escape_detected: bool = False,
) -> bool:
    """
    Enforce canonical real-path containment.

    The final resolved path must remain inside the mission-scoped VFS boundary.
    Symlink/hardlink escape flags fail closed even if a caller attempts to hide
    the escape through relative path tricks.
    """
    if symlink_detected:
        raise SessionVFSPolicyViolation("session_vfs_symlink_escape_detected")

    if hardlink_escape_detected:
        raise SessionVFSPolicyViolation("session_vfs_hardlink_escape_detected")

    boundary = Path(mission_vfs_boundary_path(ctx=ctx, base_root=base_root)).resolve()
    target = Path(candidate_path).resolve()

    try:
        target.relative_to(boundary)
    except ValueError as exc:
        raise SessionVFSPolicyViolation(
            f"session_vfs_real_path_escape_detected:{target}"
        ) from exc

    return True


def transfer_authorization_token(
    *,
    source_mission_id: str,
    target_mission_id: str,
    approving_human: str,
    approval_hash: str,
) -> str:
    return _hash(
        {
            "source_mission_id": source_mission_id,
            "target_mission_id": target_mission_id,
            "approving_human": approving_human,
            "approval_hash": approval_hash,
        }
    )


def attach_transfer_authorization_token(approval: dict[str, Any]) -> dict[str, Any]:
    token = transfer_authorization_token(
        source_mission_id=str(approval.get("source_mission_id", "")),
        target_mission_id=str(approval.get("target_mission_id", "")),
        approving_human=str(approval.get("approved_by", "")),
        approval_hash=str(approval.get("approval_hash", "")),
    )
    enriched = dict(approval)
    enriched["transfer_authorization_token"] = token
    return enriched


def verify_transfer_authorization_token(approval: dict[str, Any]) -> bool:
    expected = transfer_authorization_token(
        source_mission_id=str(approval.get("source_mission_id", "")),
        target_mission_id=str(approval.get("target_mission_id", "")),
        approving_human=str(approval.get("approved_by", "")),
        approval_hash=str(approval.get("approval_hash", "")),
    )
    return approval.get("transfer_authorization_token") == expected


def can_transfer_between_missions_with_token(
    *,
    source_record: dict[str, Any],
    target_ctx: SessionVFSContext,
    approval: dict[str, Any] | None = None,
) -> bool:
    if source_record.get("mission_id") == target_ctx.mission_id:
        return True

    if not approval:
        return False

    return (
        can_transfer_between_missions(
            source_record=source_record,
            target_ctx=target_ctx,
            approval=approval,
        )
        and verify_transfer_authorization_token(approval)
    )
