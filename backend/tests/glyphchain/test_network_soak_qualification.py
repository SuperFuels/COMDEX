from __future__ import annotations

import json

import pytest

from backend.modules.consensus.network_soak_qualification import (
    NetworkSoakQualification,
    NetworkSoakQualificationError,
)


def _run(tmp_path, *, cycles=12):
    return NetworkSoakQualification(
        tmp_path / "soak", clock_ms=lambda: 1_800_000_000_000,
    ).run(
        network_count=3, cycles_per_network=cycles, restart_interval=4,
        generated_at="2026-09-27T12:00:00Z",
    )


def test_bounded_soak_exercises_restart_interruption_partition_and_isolation(tmp_path):
    report = _run(tmp_path)
    assert report["result"] == "LOCAL_BOUNDED_SOAK_PASSED"
    assert report["production_ready"] is False
    assert report["configuration"]["total_message_cycles"] == 36
    assert all(report["checks"].values())
    assert all(item["relay_queue_final_depth"] == 0 for item in report["networks"])
    assert NetworkSoakQualification.verify_report(report) is True


def test_soak_report_is_tamper_evident(tmp_path):
    report = _run(tmp_path)
    report["configuration"]["cycles_per_network"] = 999
    assert NetworkSoakQualification.verify_report(report) is False


def test_soak_report_is_exclusive_owner_only_and_content_free(tmp_path):
    report = _run(tmp_path)
    output = NetworkSoakQualification.write_report(tmp_path / "soak-report.json", report)
    assert output.stat().st_mode & 0o777 == 0o600
    raw = output.read_text(encoding="utf-8")
    encoded = raw.lower()
    for forbidden in ("signer_email", "document_body", "legal_matter", "attachment_bytes"):
        assert forbidden not in encoded
    assert NetworkSoakQualification.verify_report(json.loads(raw)) is True
    with pytest.raises(FileExistsError):
        NetworkSoakQualification.write_report(output, report)


@pytest.mark.parametrize(
    ("networks", "cycles", "interval", "message"),
    [(1, 8, 2, "network count"), (9, 8, 2, "network count"), (2, 7, 2, "cycles"),
     (2, 5001, 2, "cycles"), (2, 8, 0, "restart interval"), (2, 8, 9, "restart interval")],
)
def test_invalid_soak_bounds_fail_closed(tmp_path, networks, cycles, interval, message):
    with pytest.raises(NetworkSoakQualificationError, match=message):
        NetworkSoakQualification(tmp_path / f"invalid-{networks}-{cycles}-{interval}").run(
            network_count=networks, cycles_per_network=cycles, restart_interval=interval,
        )


def test_soak_root_must_be_empty_and_not_a_symlink(tmp_path):
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "state").write_text("x", encoding="utf-8")
    with pytest.raises(NetworkSoakQualificationError, match="must be empty"):
        NetworkSoakQualification(occupied).run(
            network_count=2, cycles_per_network=8, restart_interval=2,
        )
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(NetworkSoakQualificationError, match="symlink refused"):
        NetworkSoakQualification(link).run(
            network_count=2, cycles_per_network=8, restart_interval=2,
        )
