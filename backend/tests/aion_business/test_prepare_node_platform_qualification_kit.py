from __future__ import annotations

import json
from datetime import UTC, datetime

from backend.modules.aion_business.runtime.node_platform_qualification import (
    REQUIRED_QUALIFICATION_CASES,
)
from scripts.prepare_node_platform_qualification_kit import (
    TARGETS,
    prepare_node_platform_qualification_kit,
)


def test_qualification_kit_hashes_exact_artifacts_and_starts_fail_closed(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    version = "0.15.0"
    for _target_id, (_system, _architecture, template) in TARGETS.items():
        (dist / template.format(version=version)).write_bytes(template.encode("utf-8"))
    output = tmp_path / "kit"
    readiness = prepare_node_platform_qualification_kit(
        dist_root=dist,
        output_root=output,
        reproducible_target_ids={"windows-x64", "linux-x64"},
        prepared_at=datetime(2026, 10, 18, tzinfo=UTC),
    )
    assert readiness["production_release_eligible"] is False
    assert readiness["fail_closed"] is True
    targets = {item["target_id"]: item for item in readiness["targets"]}
    assert targets["windows-x64"]["reproducible_build_verified"] is True
    assert targets["macos-arm64"]["reproducible_build_verified"] is False
    assert "reproducible_build_not_verified" in targets["macos-arm64"]["blockers"]
    manifest = json.loads((output / "candidate-release-manifest.json").read_text())
    assert manifest["release_stage"] == "unsigned-candidate"
    assert manifest["customer_data_included"] is False
    for target_id in TARGETS:
        spec = json.loads((output / target_id / "evidence-spec.json").read_text())
        assert spec["clean_machine"] is False
        assert set(spec["cases"]) == set(REQUIRED_QUALIFICATION_CASES)
        assert {case["status"] for case in spec["cases"].values()} == {"not-run"}
        assert all(value is False for value in spec["platform_trust"].values())
        assert all(value is False for value in spec["vault_boundary"].values())


def test_qualification_kit_reports_missing_artifacts(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    readiness = prepare_node_platform_qualification_kit(
        dist_root=dist,
        output_root=tmp_path / "kit",
        prepared_at=datetime(2026, 10, 18, tzinfo=UTC),
    )
    assert all(item["artifact_present"] is False for item in readiness["targets"])
    assert all("artifact_missing" in item["blockers"] for item in readiness["targets"])
