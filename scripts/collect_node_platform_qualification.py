#!/usr/bin/env python3
"""Collect content-free local evidence for later release-lab approval and signing."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from typing import Any, Mapping

from backend.modules.aion_business.runtime.node_platform_qualification import (
    REQUIRED_QUALIFICATION_CASES,
    NodePlatformQualificationError,
    build_node_platform_qualification,
)


SYSTEM_NAMES = {"darwin": "darwin", "windows": "windows", "linux": "linux"}
ARCHITECTURE_NAMES = {
    "amd64": "x86_64",
    "x86_64": "x86_64",
    "x64": "x86_64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _observed_platform() -> tuple[str, str]:
    system = SYSTEM_NAMES.get(platform.system().strip().lower(), "")
    architecture = ARCHITECTURE_NAMES.get(platform.machine().strip().lower(), "")
    if not system or not architecture:
        raise NodePlatformQualificationError(
            "node_qualification_observed_platform_unsupported"
        )
    return system, architecture


def collect_node_platform_qualification(
    *,
    release_manifest: Mapping[str, Any],
    target_id: str,
    artifact_path: str | Path,
    evidence_spec: Mapping[str, Any],
    observed_system: str | None = None,
    observed_architecture: str | None = None,
) -> dict[str, Any]:
    target = next(
        (
            item for item in release_manifest.get("targets") or []
            if item.get("target_id") == target_id
        ),
        None,
    )
    if target is None:
        raise NodePlatformQualificationError("node_qualification_target_missing")
    artifact = Path(artifact_path).expanduser().resolve()
    if not artifact.is_file():
        raise NodePlatformQualificationError("node_qualification_artifact_missing")
    artifact_digest = _sha256(artifact)
    artifact_bytes = artifact.stat().st_size
    if (
        artifact_digest != str(target.get("sha256") or "")
        or artifact_bytes != int(target.get("artifact_bytes") or -1)
    ):
        raise NodePlatformQualificationError(
            "node_qualification_artifact_manifest_mismatch"
        )
    if observed_system is None or observed_architecture is None:
        detected_system, detected_architecture = _observed_platform()
    else:
        detected_system, detected_architecture = observed_system, observed_architecture
    actual_system = observed_system or detected_system
    actual_architecture = observed_architecture or detected_architecture
    architectures = list(target.get("architectures") or [])
    if len(architectures) != 1:
        raise NodePlatformQualificationError(
            "node_qualification_target_architecture_ambiguous"
        )
    source_cases = evidence_spec.get("cases")
    if not isinstance(source_cases, Mapping) or set(source_cases) != set(
        REQUIRED_QUALIFICATION_CASES
    ):
        raise NodePlatformQualificationError("node_qualification_cases_incomplete")
    cases: dict[str, dict[str, object]] = {}
    for case_id in REQUIRED_QUALIFICATION_CASES:
        source = source_cases[case_id]
        if not isinstance(source, Mapping) or set(source) != {
            "status", "evidence_file", "note_code"
        }:
            raise NodePlatformQualificationError(
                f"node_qualification_case_invalid:{case_id}"
            )
        evidence_file = Path(str(source["evidence_file"])).expanduser().resolve()
        if not evidence_file.is_file():
            raise NodePlatformQualificationError(
                f"node_qualification_evidence_missing:{case_id}"
            )
        cases[case_id] = {
            "status": source["status"],
            "evidence_sha256": _sha256(evidence_file),
            "note_code": source["note_code"],
        }
    return build_node_platform_qualification(
        qualification_id=evidence_spec.get("qualification_id", ""),
        release_version=str(release_manifest.get("version") or ""),
        target_id=target_id,
        artifact_sha256=artifact_digest,
        artifact_bytes=artifact_bytes,
        declared_system=str(target.get("system") or ""),
        declared_architecture=architectures[0],
        observed_system=actual_system,
        observed_architecture=actual_architecture,
        profile=evidence_spec.get("profile", ""),
        clean_machine=evidence_spec.get("clean_machine"),
        started_at=evidence_spec.get("started_at", ""),
        completed_at=evidence_spec.get("completed_at", ""),
        qualified_by=evidence_spec.get("qualified_by", ""),
        cases=cases,
        platform_trust=evidence_spec.get("platform_trust") or {},
        vault_boundary=evidence_spec.get("vault_boundary") or {},
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect a bounded unsigned Node qualification payload. "
            "Release-lab signing is a separate step."
        )
    )
    parser.add_argument("--release-manifest", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--evidence-spec", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = json.loads(Path(args.release_manifest).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence_spec).read_text(encoding="utf-8"))
    report = collect_node_platform_qualification(
        release_manifest=manifest,
        target_id=args.target_id,
        artifact_path=args.artifact,
        evidence_spec=evidence,
    )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "Unsigned local qualification evidence written. "
        "It is not production evidence until the release-lab authority verifies and signs it."
    )
    return 0 if report["eligible"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
