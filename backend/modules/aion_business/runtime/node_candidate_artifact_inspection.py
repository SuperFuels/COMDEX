from __future__ import annotations

import hashlib
import json
import stat
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


MAX_MEMBERS = 10_000
MAX_UNCOMPRESSED_BYTES = 8 * 1024 * 1024 * 1024


class NodeCandidateArtifactInspectionError(ValueError):
    pass


def _safe_member_name(raw: str) -> PurePosixPath:
    if not raw or "\\" in raw:
        raise NodeCandidateArtifactInspectionError("candidate_archive_member_path_invalid")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise NodeCandidateArtifactInspectionError("candidate_archive_member_path_unsafe")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _platform_manifest(raw: bytes, *, target_id: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NodeCandidateArtifactInspectionError(
            "candidate_platform_manifest_invalid"
        ) from exc
    expected = {
        "clean_machine_validated",
        "contains_customer_data",
        "network",
        "platform",
        "publisher_signature",
        "service",
        "status",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise NodeCandidateArtifactInspectionError("candidate_platform_manifest_schema_invalid")
    if (
        value["platform"] != target_id
        or value["contains_customer_data"] is not False
        or value["network"] != "loopback-only"
        or value["status"] != "developer-preview-unsigned-unqualified"
        or value["publisher_signature"] is not False
        or value["clean_machine_validated"] is not False
    ):
        raise NodeCandidateArtifactInspectionError("candidate_platform_manifest_claim_invalid")
    return value


def inspect_node_candidate_archive(
    artifact_path: str | Path, *, target_id: str
) -> dict[str, Any]:
    """Inspect archive structure without extracting or trusting member paths."""
    artifact = Path(artifact_path).expanduser().resolve()
    if not artifact.is_file():
        raise NodeCandidateArtifactInspectionError("candidate_artifact_missing")
    names: list[PurePosixPath] = []
    total_bytes = 0
    manifest_bytes: bytes | None = None

    if target_id == "windows-x64":
        try:
            with zipfile.ZipFile(artifact) as archive:
                members = archive.infolist()
                if not members or len(members) > MAX_MEMBERS:
                    raise NodeCandidateArtifactInspectionError("candidate_archive_member_count_invalid")
                seen: set[str] = set()
                for member in members:
                    name = _safe_member_name(member.filename)
                    folded = name.as_posix().casefold()
                    if folded in seen:
                        raise NodeCandidateArtifactInspectionError("candidate_archive_duplicate_member")
                    seen.add(folded)
                    mode = (member.external_attr >> 16) & 0xFFFF
                    if stat.S_ISLNK(mode):
                        raise NodeCandidateArtifactInspectionError("candidate_archive_link_forbidden")
                    if member.file_size < 0 or member.file_size > MAX_UNCOMPRESSED_BYTES:
                        raise NodeCandidateArtifactInspectionError("candidate_archive_member_size_invalid")
                    total_bytes += member.file_size
                    names.append(name)
                    if name.name == "platform-manifest.json":
                        manifest_bytes = archive.read(member)
        except zipfile.BadZipFile as exc:
            raise NodeCandidateArtifactInspectionError("candidate_archive_invalid") from exc
        required = {"Install-Pilot-Windows.ps1", "platform-manifest.json"}
    elif target_id == "linux-x64":
        try:
            with tarfile.open(artifact, "r:gz") as archive:
                members = archive.getmembers()
                if not members or len(members) > MAX_MEMBERS:
                    raise NodeCandidateArtifactInspectionError("candidate_archive_member_count_invalid")
                seen: set[str] = set()
                for member in members:
                    name = _safe_member_name(member.name)
                    text = name.as_posix()
                    if text in seen:
                        raise NodeCandidateArtifactInspectionError("candidate_archive_duplicate_member")
                    seen.add(text)
                    if not (member.isfile() or member.isdir()):
                        raise NodeCandidateArtifactInspectionError("candidate_archive_special_member_forbidden")
                    if member.uid != 0 or member.gid != 0 or member.mtime != 0:
                        raise NodeCandidateArtifactInspectionError("candidate_archive_metadata_not_normalized")
                    if member.mode & 0o002:
                        raise NodeCandidateArtifactInspectionError("candidate_archive_world_writable_member")
                    if member.size < 0 or member.size > MAX_UNCOMPRESSED_BYTES:
                        raise NodeCandidateArtifactInspectionError("candidate_archive_member_size_invalid")
                    total_bytes += member.size
                    names.append(name)
                    if name.name == "platform-manifest.json":
                        extracted = archive.extractfile(member)
                        manifest_bytes = extracted.read() if extracted is not None else None
        except tarfile.TarError as exc:
            raise NodeCandidateArtifactInspectionError("candidate_archive_invalid") from exc
        required = {"install-pilot-linux.sh", "pilot-aion-brain.service", "platform-manifest.json"}
    else:
        raise NodeCandidateArtifactInspectionError("candidate_archive_target_unsupported")

    if total_bytes > MAX_UNCOMPRESSED_BYTES:
        raise NodeCandidateArtifactInspectionError("candidate_archive_expansion_limit_exceeded")
    roots = {name.parts[0] for name in names}
    if len(roots) != 1:
        raise NodeCandidateArtifactInspectionError("candidate_archive_root_invalid")
    root = next(iter(roots))
    root_files = {name.name for name in names if len(name.parts) == 2}
    if not required <= root_files or manifest_bytes is None:
        raise NodeCandidateArtifactInspectionError("candidate_archive_required_member_missing")
    manifest = _platform_manifest(manifest_bytes, target_id=target_id)
    return {
        "schema_version": "tessaris.node-candidate-artifact-inspection.v1",
        "target_id": target_id,
        "artifact_sha256": _sha256(artifact),
        "artifact_bytes": artifact.stat().st_size,
        "member_count": len(names),
        "uncompressed_bytes": total_bytes,
        "single_root": True,
        "unsafe_member_count": 0,
        "contains_customer_data": False,
        "loopback_only_claim": True,
        "publisher_signature_claimed": bool(manifest["publisher_signature"]),
        "clean_machine_validated_claimed": bool(manifest["clean_machine_validated"]),
        "passed": True,
    }
