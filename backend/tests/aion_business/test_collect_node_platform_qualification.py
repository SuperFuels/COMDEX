from __future__ import annotations

import hashlib
import json

import pytest

from backend.modules.aion_business.runtime.node_platform_qualification import (
    REQUIRED_QUALIFICATION_CASES,
    NodePlatformQualificationError,
)
from scripts.collect_node_platform_qualification import (
    collect_node_platform_qualification,
)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _setup(tmp_path):
    artifact = tmp_path / "Tessaris-Windows-x64.zip"
    artifact.write_bytes(b"exact-release-artifact")
    evidence_files = {}
    for case_id in REQUIRED_QUALIFICATION_CASES:
        path = tmp_path / f"{case_id}.evidence"
        path.write_text(f"local evidence for {case_id}", encoding="utf-8")
        evidence_files[case_id] = path
    manifest = {
        "version": "1.2.3",
        "targets": [
            {
                "target_id": "windows-x64",
                "system": "windows",
                "architectures": ["x86_64"],
                "artifact_bytes": artifact.stat().st_size,
                "sha256": _sha(artifact.read_bytes()),
            }
        ],
    }
    spec = {
        "qualification_id": "qual-windows-x64-001",
        "profile": "desktop",
        "clean_machine": True,
        "started_at": "2026-10-17T18:00:00+00:00",
        "completed_at": "2026-10-17T19:00:00+00:00",
        "qualified_by": "release-lab-1",
        "cases": {
            case_id: {
                "status": "passed",
                "evidence_file": str(path),
                "note_code": "native-test-evidence",
            }
            for case_id, path in evidence_files.items()
        },
        "platform_trust": {
            "artifact_signature_valid": True,
            "service_identity_separate": True,
            "native_credential_store_verified": True,
            "no_public_inbound_admin_port": True,
        },
        "vault_boundary": {
            "roots_separate": True,
            "updater_cannot_open_vault": True,
            "guardian_cannot_write_application": True,
            "restore_hashes_and_invariants_match": True,
        },
    }
    return artifact, manifest, spec


def test_collector_hashes_local_evidence_without_exporting_paths_or_content(tmp_path):
    artifact, manifest, spec = _setup(tmp_path)
    report = collect_node_platform_qualification(
        release_manifest=manifest,
        target_id="windows-x64",
        artifact_path=artifact,
        evidence_spec=spec,
        observed_system="windows",
        observed_architecture="x86_64",
    )
    encoded = json.dumps(report)
    assert report["eligible"] is True
    assert str(tmp_path) not in encoded
    assert "local evidence for" not in encoded
    assert report["cases"]["clean_install"]["evidence_sha256"] == _sha(
        (tmp_path / "clean_install.evidence").read_bytes()
    )


def test_collector_records_wrong_native_platform_as_ineligible(tmp_path):
    artifact, manifest, spec = _setup(tmp_path)
    report = collect_node_platform_qualification(
        release_manifest=manifest,
        target_id="windows-x64",
        artifact_path=artifact,
        evidence_spec=spec,
        observed_system="linux",
        observed_architecture="x86_64",
    )
    assert report["eligible"] is False
    assert "observed_system_mismatch" in report["reasons"]


def test_collector_rejects_artifact_or_missing_local_evidence(tmp_path):
    artifact, manifest, spec = _setup(tmp_path)
    artifact.write_bytes(b"tampered")
    with pytest.raises(NodePlatformQualificationError, match="manifest_mismatch"):
        collect_node_platform_qualification(
            release_manifest=manifest,
            target_id="windows-x64",
            artifact_path=artifact,
            evidence_spec=spec,
            observed_system="windows",
            observed_architecture="x86_64",
        )
    artifact, manifest, spec = _setup(tmp_path)
    (tmp_path / "clean_install.evidence").unlink()
    with pytest.raises(NodePlatformQualificationError, match="evidence_missing"):
        collect_node_platform_qualification(
            release_manifest=manifest,
            target_id="windows-x64",
            artifact_path=artifact,
            evidence_spec=spec,
            observed_system="windows",
            observed_architecture="x86_64",
        )
