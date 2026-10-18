from __future__ import annotations

import json

import pytest

from backend.modules.consensus.network_qualification import (
    NetworkQualificationError,
    NetworkQualificationExercise,
)


RELEASE = "ab" * 32


def _run(tmp_path):
    return NetworkQualificationExercise(
        tmp_path / "exercise", clock_ms=lambda: 1_800_000_000_000,
    ).run(
        release_manifest_sha256=RELEASE,
        validator_checkpoint_id="checkpoint-production-candidate",
        governance_approval_id="approval-production-candidate",
        generated_at="2026-09-27T10:00:00Z",
    )


def test_local_network_qualification_exercises_all_bounded_controls(tmp_path):
    report = _run(tmp_path)
    assert report["result"] == "LOCAL_PREPRODUCTION_EXERCISE_PASSED"
    assert report["production_ready"] is False
    assert report["content_free"] is True
    assert report["logical_profiles"] == ["home", "office", "vm", "intermittent"]
    assert all(report["checks"].values())
    assert report["relay"]["legal_content_present"] is False
    assert report["protocol_upgrade"]["release_manifest_sha256"] == RELEASE
    assert NetworkQualificationExercise.verify_report(report) is True


def test_report_tampering_is_detected(tmp_path):
    report = _run(tmp_path)
    report["checks"]["partition_conflict_failed_closed"] = False
    assert NetworkQualificationExercise.verify_report(report) is False


def test_report_is_owner_only_exclusive_and_contains_no_private_legal_fields(tmp_path):
    report = _run(tmp_path)
    output = tmp_path / "network-report.json"
    NetworkQualificationExercise.write_report(output, report)
    assert output.stat().st_mode & 0o777 == 0o600
    encoded = output.read_text(encoding="utf-8").lower()
    for forbidden in ("signer_email", "document_body", "legal_matter", "attachment_bytes"):
        assert forbidden not in encoded
    with pytest.raises(FileExistsError):
        NetworkQualificationExercise.write_report(output, report)


def test_invalid_release_digest_and_missing_authority_bindings_fail_closed(tmp_path):
    exercise = NetworkQualificationExercise(tmp_path / "exercise")
    with pytest.raises(NetworkQualificationError, match="exact SHA-256"):
        exercise.run(
            release_manifest_sha256="not-a-digest",
            validator_checkpoint_id="checkpoint",
            governance_approval_id="approval",
        )
    exercise = NetworkQualificationExercise(tmp_path / "exercise-two")
    with pytest.raises(NetworkQualificationError, match="identifiers are required"):
        exercise.run(
            release_manifest_sha256=RELEASE,
            validator_checkpoint_id="",
            governance_approval_id="approval",
        )


def test_exercise_root_must_be_empty_and_symlink_free(tmp_path):
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "existing").write_text("state", encoding="utf-8")
    with pytest.raises(NetworkQualificationError, match="must be empty"):
        NetworkQualificationExercise(occupied).run(
            release_manifest_sha256=RELEASE,
            validator_checkpoint_id="checkpoint",
            governance_approval_id="approval",
        )
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(NetworkQualificationError, match="symlink refused"):
        NetworkQualificationExercise(link).run(
            release_manifest_sha256=RELEASE,
            validator_checkpoint_id="checkpoint",
            governance_approval_id="approval",
        )


def test_report_round_trip_verifies(tmp_path):
    report = _run(tmp_path)
    output = NetworkQualificationExercise.write_report(tmp_path / "report.json", report)
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert NetworkQualificationExercise.verify_report(loaded) is True
