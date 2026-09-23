import pytest

from backend.services.aion_mission_mode.business_container_artifacts import (
    ALLOWED_BUSINESS_SUB_CONTAINERS,
    BusinessArtifactTarget,
    PilotArtifactProvenance,
    business_container_path,
    commit_pilot_artifact_to_business_container,
    validate_pilot_artifact_record,
)


def make_target(sub_container: str = "campaigns", artifact_type: str = "advert_draft") -> BusinessArtifactTarget:
    return BusinessArtifactTarget(
        business_id="home_fixed",
        business_container_id="business_home_fixed",
        sub_container=sub_container,
        artifact_type=artifact_type,
        artifact_name="facebook_advert_draft",
    )


def make_provenance() -> PilotArtifactProvenance:
    return PilotArtifactProvenance(
        mission_id="mission_home_fixed_lead_campaign_001",
        mission_run_id="run_001",
        step_id="step_03_draft_facebook_advert",
        tool_id="pilot_campaign_draft_tool",
    )


def test_phase20aa_allowed_sub_containers_are_locked() -> None:
    assert ALLOWED_BUSINESS_SUB_CONTAINERS == {
        "missions",
        "campaigns",
        "quotes",
        "workflows",
        "agentmaps",
        "reports",
        "evidence",
        "exports",
        "approvals",
        "receipts",
    }


def test_phase20aa_business_container_path_is_inside_business_container() -> None:
    target = make_target()
    path = business_container_path(target, "artifact_abc")

    assert path == "business_containers/business_home_fixed/campaigns/artifact_abc.json"


def test_phase20aa_commit_artifact_adds_required_provenance_and_hashes() -> None:
    record = commit_pilot_artifact_to_business_container(
        target=make_target(),
        provenance=make_provenance(),
        artifact_payload={"headline": "Roof repairs and outdoor living upgrades", "status": "draft"},
        source_payload={"source": "mission_planner"},
    )

    assert record["target"]["business_id"] == "home_fixed"
    assert record["target"]["business_container_id"] == "business_home_fixed"
    assert record["target"]["sub_container"] == "campaigns"
    assert record["provenance"]["created_by"] == "aion_pilot"
    assert record["provenance"]["mission_id"] == "mission_home_fixed_lead_campaign_001"
    assert record["artifact_hash"]
    assert record["source_payload_hash"]
    assert record["receipt_hash"]
    assert validate_pilot_artifact_record(record) is True


def test_phase20aa_rejects_global_or_session_vfs_as_final_target() -> None:
    for bad_container in ["global", "root", "session_vfs", "tmp", "temp"]:
        with pytest.raises(ValueError):
            commit_pilot_artifact_to_business_container(
                target=BusinessArtifactTarget(
                    business_id="home_fixed",
                    business_container_id=bad_container,
                    sub_container="campaigns",
                    artifact_type="advert_draft",
                    artifact_name="bad",
                ),
                provenance=make_provenance(),
                artifact_payload={"draft": "bad"},
            )


def test_phase20aa_rejects_invalid_sub_container() -> None:
    with pytest.raises(ValueError):
        commit_pilot_artifact_to_business_container(
            target=make_target(sub_container="random_global_folder"),
            provenance=make_provenance(),
            artifact_payload={"draft": "bad"},
        )


def test_phase20aa_rejects_unknown_artifact_type() -> None:
    with pytest.raises(ValueError):
        commit_pilot_artifact_to_business_container(
            target=make_target(artifact_type="unknown_blob"),
            provenance=make_provenance(),
            artifact_payload={"draft": "bad"},
        )


def test_phase20aa_rejects_non_pilot_creator() -> None:
    with pytest.raises(ValueError):
        commit_pilot_artifact_to_business_container(
            target=make_target(),
            provenance=PilotArtifactProvenance(
                mission_id="mission_001",
                mission_run_id="run_001",
                step_id="step_001",
                tool_id="manual_tool",
                created_by="external_agent",
            ),
            artifact_payload={"draft": "bad"},
        )


def test_phase20aa_session_vfs_only_record_is_not_valid_final_artifact() -> None:
    record = commit_pilot_artifact_to_business_container(
        target=make_target(),
        provenance=make_provenance(),
        artifact_payload={"draft": "ok"},
    )
    record["session_vfs_only"] = True
    record["storage_state"] = "session_vfs_draft"

    assert validate_pilot_artifact_record(record) is False


def test_phase20aa_record_path_must_match_business_container_and_sub_container() -> None:
    record = commit_pilot_artifact_to_business_container(
        target=make_target(sub_container="campaigns"),
        provenance=make_provenance(),
        artifact_payload={"draft": "ok"},
    )
    record["storage_path"] = "business_containers/business_home_fixed/reports/artifact_wrong.json"

    assert validate_pilot_artifact_record(record) is False


def test_phase20aa_hashes_are_deterministic() -> None:
    first = commit_pilot_artifact_to_business_container(
        target=make_target(),
        provenance=make_provenance(),
        artifact_payload={"draft": "same"},
    )
    second = commit_pilot_artifact_to_business_container(
        target=make_target(),
        provenance=make_provenance(),
        artifact_payload={"draft": "same"},
    )

    assert first["artifact_id"] == second["artifact_id"]
    assert first["artifact_hash"] == second["artifact_hash"]
    assert first["receipt_hash"] == second["receipt_hash"]


def test_phase20aa1_canonical_path_stays_inside_business_container(tmp_path) -> None:
    from backend.services.aion_mission_mode.business_container_artifacts import (
        canonical_artifact_real_path,
    )

    target = make_target()
    real_path = canonical_artifact_real_path(
        platform_root=str(tmp_path),
        target=target,
        artifact_id="artifact_safe",
    )

    assert str(real_path).startswith(
        str(tmp_path / "business_containers" / "business_home_fixed")
    )
    assert real_path.name == "artifact_safe.json"


def test_phase20aa1_rejects_artifact_id_directory_traversal(tmp_path) -> None:
    from backend.services.aion_mission_mode.business_container_artifacts import (
        ArtifactPathContainmentError,
        canonical_artifact_real_path,
    )

    with pytest.raises(ArtifactPathContainmentError):
        canonical_artifact_real_path(
            platform_root=str(tmp_path),
            target=make_target(),
            artifact_id="../../escape",
        )


def test_phase20aa1_rejects_windows_style_namespace_smuggling(tmp_path) -> None:
    from backend.services.aion_mission_mode.business_container_artifacts import (
        validate_artifact_target,
        BusinessArtifactTarget,
    )

    with pytest.raises(ValueError):
        validate_artifact_target(
            BusinessArtifactTarget(
                business_id="home_fixed",
                business_container_id="business_home_fixed",
                sub_container="..\\..\\escape",
                artifact_type="advert_draft",
                artifact_name="bad",
            )
        )


def test_phase20aa1_artifact_merkle_triad_validates() -> None:
    from backend.services.aion_mission_mode.business_container_artifacts import (
        validate_artifact_merkle_triad,
    )

    record = commit_pilot_artifact_to_business_container(
        target=make_target(),
        provenance=make_provenance(),
        artifact_payload={"draft": "triad"},
        source_payload={"source": "planner"},
    )

    assert validate_artifact_merkle_triad(record) is True


def test_phase20aa1_artifact_merkle_triad_detects_tampering() -> None:
    from backend.services.aion_mission_mode.business_container_artifacts import (
        validate_artifact_merkle_triad,
    )

    record = commit_pilot_artifact_to_business_container(
        target=make_target(),
        provenance=make_provenance(),
        artifact_payload={"draft": "triad"},
        source_payload={"source": "planner"},
    )

    record["storage_path"] = "business_containers/business_home_fixed/reports/tampered.json"

    assert validate_artifact_merkle_triad(record) is False
