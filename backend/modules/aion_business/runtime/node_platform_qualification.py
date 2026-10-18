from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


NODE_PLATFORM_QUALIFICATION_SCHEMA = "tessaris.node-platform-qualification.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
NOTE_CODE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
SYSTEMS = {"darwin", "windows", "linux"}
ARCHITECTURES = {"x86_64", "arm64"}
PROFILES = {
    "desktop",
    "headless-node",
    "private-cloud",
    "hub",
    "rack-authority",
    "sovereign-offline",
}
CASE_STATES = {"passed", "failed", "not-run"}
REQUIRED_QUALIFICATION_CASES = (
    "clean_install",
    "first_run_vault_and_recovery",
    "service_restart_after_reboot",
    "bounded_business_workflow",
    "signed_update",
    "automatic_rollback",
    "vault_preserved_across_update",
    "backup_restore_on_clean_machine",
    "authority_move_and_old_node_fencing",
    "uninstall_preserves_vault",
    "reinstall_reconnects_vault",
    "export_without_entitlement",
    "commercial_expiry_preserves_ownership",
)
TRUST_KEYS = {
    "artifact_signature_valid",
    "service_identity_separate",
    "native_credential_store_verified",
    "no_public_inbound_admin_port",
}
VAULT_BOUNDARY_KEYS = {
    "roots_separate",
    "updater_cannot_open_vault",
    "guardian_cannot_write_application",
    "restore_hashes_and_invariants_match",
}
REPORT_KEYS = {
    "schema_version",
    "qualification_id",
    "release_version",
    "target_id",
    "artifact_sha256",
    "artifact_bytes",
    "declared_system",
    "declared_architecture",
    "observed_system",
    "observed_architecture",
    "profile",
    "clean_machine",
    "started_at",
    "completed_at",
    "qualified_by",
    "cases",
    "platform_trust",
    "vault_boundary",
    "eligible",
    "reasons",
    "content_free",
    "customer_content_included",
}


class NodePlatformQualificationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def node_platform_qualification_envelope_sha256(
    envelope: Mapping[str, Any],
) -> str:
    return hashlib.sha256(_canonical(dict(envelope))).hexdigest()


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _instant(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise NodePlatformQualificationError(
            "node_qualification_datetime_invalid"
        ) from exc
    if result.tzinfo is None:
        raise NodePlatformQualificationError(
            "node_qualification_datetime_timezone_required"
        )
    return result.astimezone(UTC)


def _safe_id(value: object, field: str) -> str:
    result = str(value or "").strip()
    if not SAFE_ID.fullmatch(result):
        raise NodePlatformQualificationError(f"node_qualification_{field}_invalid")
    return result


def build_node_platform_qualification(
    *,
    qualification_id: str,
    release_version: str,
    target_id: str,
    artifact_sha256: str,
    artifact_bytes: int,
    declared_system: str,
    declared_architecture: str,
    observed_system: str,
    observed_architecture: str,
    profile: str,
    clean_machine: bool,
    started_at: str,
    completed_at: str,
    qualified_by: str,
    cases: Mapping[str, Mapping[str, object]],
    platform_trust: Mapping[str, object],
    vault_boundary: Mapping[str, object],
) -> dict[str, Any]:
    qualification_id = _safe_id(qualification_id, "id")
    release_version = _safe_id(release_version, "release_version")
    target_id = _safe_id(target_id, "target_id")
    qualified_by = _safe_id(qualified_by, "qualified_by")
    if not DIGEST.fullmatch(str(artifact_sha256 or "")) or int(artifact_bytes) < 1:
        raise NodePlatformQualificationError("node_qualification_artifact_invalid")
    declared_system = str(declared_system or "").strip().lower()
    observed_system = str(observed_system or "").strip().lower()
    declared_architecture = str(declared_architecture or "").strip().lower()
    observed_architecture = str(observed_architecture or "").strip().lower()
    if declared_system not in SYSTEMS or observed_system not in SYSTEMS:
        raise NodePlatformQualificationError("node_qualification_system_invalid")
    if (
        declared_architecture not in ARCHITECTURES
        or observed_architecture not in ARCHITECTURES
    ):
        raise NodePlatformQualificationError("node_qualification_architecture_invalid")
    if profile not in PROFILES:
        raise NodePlatformQualificationError("node_qualification_profile_invalid")
    if not isinstance(clean_machine, bool):
        raise NodePlatformQualificationError("node_qualification_clean_machine_invalid")
    started = _instant(started_at)
    completed = _instant(completed_at)
    if completed <= started:
        raise NodePlatformQualificationError("node_qualification_time_window_invalid")
    if set(cases) != set(REQUIRED_QUALIFICATION_CASES):
        raise NodePlatformQualificationError("node_qualification_cases_incomplete")
    normalized_cases: dict[str, dict[str, object]] = {}
    for case_id in REQUIRED_QUALIFICATION_CASES:
        source = cases[case_id]
        if not isinstance(source, Mapping) or set(source) != {
            "status", "evidence_sha256", "note_code"
        }:
            raise NodePlatformQualificationError(
                f"node_qualification_case_invalid:{case_id}"
            )
        status = str(source["status"])
        digest = str(source["evidence_sha256"])
        note_code = str(source["note_code"])
        if status not in CASE_STATES or not DIGEST.fullmatch(digest):
            raise NodePlatformQualificationError(
                f"node_qualification_case_invalid:{case_id}"
            )
        if not NOTE_CODE.fullmatch(note_code):
            raise NodePlatformQualificationError(
                f"node_qualification_note_code_invalid:{case_id}"
            )
        normalized_cases[case_id] = {
            "status": status,
            "evidence_sha256": digest,
            "note_code": note_code,
        }
    if set(platform_trust) != TRUST_KEYS or any(
        not isinstance(value, bool) for value in platform_trust.values()
    ):
        raise NodePlatformQualificationError("node_qualification_platform_trust_invalid")
    if set(vault_boundary) != VAULT_BOUNDARY_KEYS or any(
        not isinstance(value, bool) for value in vault_boundary.values()
    ):
        raise NodePlatformQualificationError("node_qualification_vault_boundary_invalid")

    reasons: list[str] = []
    if not clean_machine:
        reasons.append("clean_machine_not_proven")
    if declared_system != observed_system:
        reasons.append("observed_system_mismatch")
    if declared_architecture != observed_architecture:
        reasons.append("observed_architecture_mismatch")
    reasons.extend(
        f"qualification_case_{case_id}_{normalized_cases[case_id]['status']}"
        for case_id in REQUIRED_QUALIFICATION_CASES
        if normalized_cases[case_id]["status"] != "passed"
    )
    reasons.extend(
        f"platform_trust_{key}_failed"
        for key in sorted(TRUST_KEYS)
        if platform_trust[key] is not True
    )
    reasons.extend(
        f"vault_boundary_{key}_failed"
        for key in sorted(VAULT_BOUNDARY_KEYS)
        if vault_boundary[key] is not True
    )
    return {
        "schema_version": NODE_PLATFORM_QUALIFICATION_SCHEMA,
        "qualification_id": qualification_id,
        "release_version": release_version,
        "target_id": target_id,
        "artifact_sha256": artifact_sha256,
        "artifact_bytes": int(artifact_bytes),
        "declared_system": declared_system,
        "declared_architecture": declared_architecture,
        "observed_system": observed_system,
        "observed_architecture": observed_architecture,
        "profile": profile,
        "clean_machine": bool(clean_machine),
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "qualified_by": qualified_by,
        "cases": normalized_cases,
        "platform_trust": {key: bool(platform_trust[key]) for key in sorted(TRUST_KEYS)},
        "vault_boundary": {
            key: bool(vault_boundary[key]) for key in sorted(VAULT_BOUNDARY_KEYS)
        },
        "eligible": not reasons,
        "reasons": reasons,
        "content_free": True,
        "customer_content_included": False,
    }


def sign_node_platform_qualification(
    report: Mapping[str, Any], *, private_key: Ed25519PrivateKey
) -> dict[str, Any]:
    payload = validate_node_platform_qualification_payload(report)
    return {
        "payload": payload,
        "signature": _b64(private_key.sign(_canonical(payload))),
    }


def validate_node_platform_qualification_payload(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(report)
    if set(payload) != REPORT_KEYS or payload.get(
        "schema_version"
    ) != NODE_PLATFORM_QUALIFICATION_SCHEMA:
        raise NodePlatformQualificationError("node_qualification_schema_invalid")
    rebuilt = build_node_platform_qualification(
        qualification_id=payload["qualification_id"],
        release_version=payload["release_version"],
        target_id=payload["target_id"],
        artifact_sha256=payload["artifact_sha256"],
        artifact_bytes=payload["artifact_bytes"],
        declared_system=payload["declared_system"],
        declared_architecture=payload["declared_architecture"],
        observed_system=payload["observed_system"],
        observed_architecture=payload["observed_architecture"],
        profile=payload["profile"],
        clean_machine=payload["clean_machine"],
        started_at=payload["started_at"],
        completed_at=payload["completed_at"],
        qualified_by=payload["qualified_by"],
        cases=payload["cases"],
        platform_trust=payload["platform_trust"],
        vault_boundary=payload["vault_boundary"],
    )
    if payload != rebuilt:
        raise NodePlatformQualificationError("node_qualification_derived_state_invalid")
    return rebuilt


def verify_node_platform_qualification(
    envelope: Mapping[str, Any],
    *,
    public_key: Ed25519PublicKey,
    release_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    payload = validate_node_platform_qualification_payload(
        dict(envelope.get("payload") or {})
    )
    try:
        public_key.verify(
            _unb64(str(envelope.get("signature") or "")), _canonical(payload)
        )
    except (InvalidSignature, ValueError) as exc:
        raise NodePlatformQualificationError(
            "node_qualification_signature_invalid"
        ) from exc
    if payload["release_version"] != str(release_manifest.get("version") or ""):
        raise NodePlatformQualificationError("node_qualification_release_mismatch")
    target = next(
        (
            item for item in release_manifest.get("targets") or []
            if item.get("target_id") == payload["target_id"]
        ),
        None,
    )
    if target is None:
        raise NodePlatformQualificationError("node_qualification_target_missing")
    if (
        target.get("system") != payload["declared_system"]
        or payload["declared_architecture"] not in set(target.get("architectures") or [])
        or str(target.get("sha256") or "") != payload["artifact_sha256"]
        or int(target.get("artifact_bytes") or -1) != payload["artifact_bytes"]
    ):
        raise NodePlatformQualificationError("node_qualification_artifact_mismatch")
    qualification_digest = str(target.get("qualification_report_sha256") or "")
    if qualification_digest and qualification_digest != node_platform_qualification_envelope_sha256(
        envelope
    ):
        raise NodePlatformQualificationError(
            "node_qualification_report_digest_mismatch"
        )
    if payload["eligible"] is not True:
        raise NodePlatformQualificationError("node_platform_not_qualified")
    return payload
