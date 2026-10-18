#!/usr/bin/env python3
"""Prepare exact-artifact, fail-closed clean-machine qualification workspaces."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from backend.modules.aion_business.runtime.node_platform_qualification import (
    REQUIRED_QUALIFICATION_CASES,
)
from backend.modules.aion_business.runtime.node_candidate_artifact_inspection import (
    NodeCandidateArtifactInspectionError,
    inspect_node_candidate_archive,
)


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PACKAGING = ROOT / "packaging" / "aion_sovereign_brain_bootstrap"
TARGETS = {
    "macos-arm64": ("darwin", "arm64", "Pilot-AION-Brain-macOS-arm64-{version}-unsigned.pkg"),
    "windows-x64": ("windows", "x86_64", "Pilot-AION-Brain-Windows-x64-{version}-unsigned.zip"),
    "linux-x64": ("linux", "x86_64", "pilot-aion-brain-linux-x64-{version}-unsigned.tar.gz"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_node_platform_qualification_kit(
    *,
    dist_root: Path = DIST,
    output_root: Path | None = None,
    reproducible_target_ids: Iterable[str] = (),
    prepared_at: datetime | None = None,
) -> dict[str, object]:
    release = json.loads((PACKAGING / "release_manifest.json").read_text(encoding="utf-8"))
    version = str(release["version"])
    prepared_at = (prepared_at or datetime.now(UTC)).astimezone(UTC)
    reproducible = set(reproducible_target_ids)
    unknown = reproducible - set(TARGETS)
    if unknown:
        raise ValueError(f"unknown_reproducible_targets:{','.join(sorted(unknown))}")
    output_root = (output_root or dist_root / f"node-qualification-kit-{version}").resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    manifest_targets = []
    readiness_targets = []
    for target_id, (system, architecture, filename_template) in TARGETS.items():
        artifact = (dist_root / filename_template.format(version=version)).resolve()
        present = artifact.is_file()
        target_blockers = ["artifact_unsigned", "native_clean_machine_not_run"]
        if target_id not in reproducible:
            target_blockers.append("reproducible_build_not_verified")
        if not present:
            target_blockers.append("artifact_missing")
        inspection = None
        if present and target_id in {"windows-x64", "linux-x64"}:
            try:
                inspection = inspect_node_candidate_archive(artifact, target_id=target_id)
            except NodeCandidateArtifactInspectionError as exc:
                inspection = {
                    "schema_version": "tessaris.node-candidate-artifact-inspection.v1",
                    "target_id": target_id,
                    "passed": False,
                    "reason_code": str(exc),
                }
                target_blockers.append("static_artifact_inspection_failed")
        elif target_id == "macos-arm64":
            target_blockers.append("native_package_inspection_not_run")
        target_entry = {
            "target_id": target_id,
            "system": system,
            "architectures": [architecture],
            "artifact_bytes": artifact.stat().st_size if present else 0,
            "sha256": _sha256(artifact) if present else "0" * 64,
        }
        manifest_targets.append(target_entry)

        target_root = output_root / target_id
        if inspection is not None:
            _write_json(target_root / "static-artifact-inspection.json", inspection)
        cases = {}
        for case_id in REQUIRED_QUALIFICATION_CASES:
            evidence_path = target_root / "evidence" / f"{case_id}.json"
            _write_json(
                evidence_path,
                {
                    "schema_version": "tessaris.node-qualification-case-evidence.v1",
                    "target_id": target_id,
                    "case_id": case_id,
                    "status": "not-run",
                    "content_free": True,
                    "customer_content_included": False,
                },
            )
            cases[case_id] = {
                "status": "not-run",
                "evidence_file": str(evidence_path.resolve()),
                "note_code": "not-run",
            }
        _write_json(
            target_root / "evidence-spec.json",
            {
                "qualification_id": f"qual-{target_id}-{version}-not-run",
                "profile": "desktop",
                "clean_machine": False,
                "started_at": prepared_at.isoformat(),
                "completed_at": (prepared_at + timedelta(microseconds=1)).isoformat(),
                "qualified_by": "qualification-not-run",
                "cases": cases,
                "platform_trust": {
                    "artifact_signature_valid": False,
                    "service_identity_separate": False,
                    "native_credential_store_verified": False,
                    "no_public_inbound_admin_port": False,
                },
                "vault_boundary": {
                    "roots_separate": False,
                    "updater_cannot_open_vault": False,
                    "guardian_cannot_write_application": False,
                    "restore_hashes_and_invariants_match": False,
                },
            },
        )
        readiness_targets.append(
            {
                **target_entry,
                "artifact_path": str(artifact),
                "artifact_present": present,
                "reproducible_build_verified": target_id in reproducible,
                "qualification_eligible": False,
                "blockers": sorted(set(target_blockers)),
                "evidence_spec": str((target_root / "evidence-spec.json").resolve()),
                "static_artifact_inspection": (
                    str((target_root / "static-artifact-inspection.json").resolve())
                    if inspection is not None
                    else None
                ),
            }
        )

    manifest = {
        "schema_version": "tessaris.node-release-manifest.v1",
        "version": version,
        "channel": "internal-qualification",
        "release_stage": "unsigned-candidate",
        "customer_data_included": False,
        "customer_credentials_included": False,
        "targets": manifest_targets,
    }
    manifest_path = output_root / "candidate-release-manifest.json"
    _write_json(manifest_path, manifest)
    readiness = {
        "schema_version": "tessaris.node-qualification-readiness.v1",
        "release_version": version,
        "prepared_at": prepared_at.isoformat(),
        "production_release_eligible": False,
        "fail_closed": True,
        "targets": readiness_targets,
        "remaining_external_gates": [
            "publisher_sign_each_exact_artifact",
            "run_all_required_cases_on_clean_native_machines",
            "verify_native_service_identity_and_credential_store",
            "verify_vault_application_updater_and_guardian_boundaries",
            "independent_release_lab_review_and_signature",
        ],
    }
    _write_json(output_root / "qualification-readiness.json", readiness)
    (output_root / "README.md").write_text(
        "# Tessaris Node qualification kit\n\n"
        "This workspace is deliberately fail-closed. Its evidence files begin at `not-run`, "
        "all trust assertions begin `false`, and every candidate is unsigned. Run each target "
        "only on a clean native machine, replace each case file with content-free observed "
        "evidence, and update the evidence spec truthfully. Then invoke "
        "`scripts/collect_node_platform_qualification.py` against the exact artifact and "
        "candidate manifest. Release-lab review and signing remain separate gates.\n",
        encoding="utf-8",
    )
    return readiness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-root", default=str(DIST))
    parser.add_argument("--output-root")
    parser.add_argument("--reproducible-target", action="append", default=[])
    args = parser.parse_args()
    readiness = prepare_node_platform_qualification_kit(
        dist_root=Path(args.dist_root).expanduser().resolve(),
        output_root=Path(args.output_root).expanduser().resolve() if args.output_root else None,
        reproducible_target_ids=args.reproducible_target,
    )
    print(json.dumps(readiness, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
