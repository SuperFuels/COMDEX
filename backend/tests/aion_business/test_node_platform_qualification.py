from __future__ import annotations

from copy import deepcopy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.node_platform_qualification import (
    REQUIRED_QUALIFICATION_CASES,
    NodePlatformQualificationError,
    build_node_platform_qualification,
    node_platform_qualification_envelope_sha256,
    sign_node_platform_qualification,
    verify_node_platform_qualification,
)


DIGEST = "a" * 64


def _cases(status: str = "passed") -> dict:
    return {
        case_id: {
            "status": status,
            "evidence_sha256": f"{index + 1:064x}",
            "note_code": "native-test-evidence",
        }
        for index, case_id in enumerate(REQUIRED_QUALIFICATION_CASES)
    }


def _report(**overrides) -> dict:
    values = {
        "qualification_id": "qual-windows-x64-001",
        "release_version": "1.2.3",
        "target_id": "windows-x64",
        "artifact_sha256": DIGEST,
        "artifact_bytes": 4096,
        "declared_system": "windows",
        "declared_architecture": "x86_64",
        "observed_system": "windows",
        "observed_architecture": "x86_64",
        "profile": "desktop",
        "clean_machine": True,
        "started_at": "2026-10-17T18:00:00+00:00",
        "completed_at": "2026-10-17T19:00:00+00:00",
        "qualified_by": "release-lab-1",
        "cases": _cases(),
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
    values.update(overrides)
    return build_node_platform_qualification(**values)


def _manifest() -> dict:
    return {
        "version": "1.2.3",
        "targets": [
            {
                "target_id": "windows-x64",
                "system": "windows",
                "architectures": ["x86_64"],
                "artifact_bytes": 4096,
                "sha256": DIGEST,
            }
        ],
    }


def test_signed_clean_machine_report_is_bound_to_exact_release_artifact():
    key = Ed25519PrivateKey.generate()
    envelope = sign_node_platform_qualification(_report(), private_key=key)
    manifest = _manifest()
    manifest["targets"][0][
        "qualification_report_sha256"
    ] = node_platform_qualification_envelope_sha256(envelope)
    verified = verify_node_platform_qualification(
        envelope, public_key=key.public_key(), release_manifest=manifest
    )
    assert verified["eligible"] is True
    assert verified["content_free"] is True
    assert verified["customer_content_included"] is False


def test_failed_or_not_run_case_cannot_qualify_platform():
    cases = _cases()
    cases["automatic_rollback"]["status"] = "not-run"
    report = _report(cases=cases)
    assert report["eligible"] is False
    assert "qualification_case_automatic_rollback_not-run" in report["reasons"]
    key = Ed25519PrivateKey.generate()
    with pytest.raises(NodePlatformQualificationError, match="not_qualified"):
        verify_node_platform_qualification(
            sign_node_platform_qualification(report, private_key=key),
            public_key=key.public_key(),
            release_manifest=_manifest(),
        )


def test_report_rejects_missing_scenario_and_platform_mismatch():
    cases = _cases()
    cases.pop("backup_restore_on_clean_machine")
    with pytest.raises(NodePlatformQualificationError, match="cases_incomplete"):
        _report(cases=cases)
    mismatch = _report(observed_system="linux")
    assert mismatch["eligible"] is False
    assert "observed_system_mismatch" in mismatch["reasons"]


def test_signature_and_manifest_binding_fail_closed():
    key = Ed25519PrivateKey.generate()
    envelope = sign_node_platform_qualification(_report(), private_key=key)
    tampered = deepcopy(envelope)
    tampered["payload"]["artifact_sha256"] = "b" * 64
    with pytest.raises(NodePlatformQualificationError):
        verify_node_platform_qualification(
            tampered, public_key=key.public_key(), release_manifest=_manifest()
        )
    wrong_manifest = _manifest()
    wrong_manifest["targets"][0]["artifact_bytes"] = 8192
    with pytest.raises(NodePlatformQualificationError, match="artifact_mismatch"):
        verify_node_platform_qualification(
            envelope, public_key=key.public_key(), release_manifest=wrong_manifest
        )
    wrong_digest_manifest = _manifest()
    wrong_digest_manifest["targets"][0]["qualification_report_sha256"] = "f" * 64
    with pytest.raises(NodePlatformQualificationError, match="report_digest_mismatch"):
        verify_node_platform_qualification(
            envelope,
            public_key=key.public_key(),
            release_manifest=wrong_digest_manifest,
        )


def test_private_or_unbounded_case_fields_are_rejected():
    cases = _cases()
    cases["clean_install"]["customer_name"] = "private customer"
    with pytest.raises(NodePlatformQualificationError, match="case_invalid"):
        _report(cases=cases)
