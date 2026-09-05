import json

from backend.services.aion_mission_mode.boardroom_session_artifacts import (
    commit_boardroom_session_artifact,
    create_boardroom_session_payload,
    create_file_cabinet_pointer_for_boardroom_session,
)


def test_phase25k_boardroom_session_payload_is_approval_gated():
    payload = create_boardroom_session_payload(
        business_id="home-fixed",
        session_id="session_001",
        session_type="business_assessment",
        business_context_packet={"business_name": "Home Fixed"},
        department_intelligence_packet={"marketing": {"status": "plan_ready"}},
        user_added_context=[{"text": "Facebook campaign next week"}],
        council_members=["AION", "Gemma"],
    )

    assert payload["schema_version"] == "aion.boardroom_session_artifact_payload.v0"
    assert payload["execution_boundary"]["approval_gated"] is True
    assert payload["execution_boundary"]["pilot_waits_for_user"] is True
    assert payload["execution_boundary"]["live_external_side_effects_performed"] is False
    assert payload["execution_boundary"]["raw_model_tool_access_allowed"] is False
    assert payload["execution_boundary"]["provider_memory_mutation_allowed"] is False
    assert payload["boardroom_session_packet_hash"].startswith("sha256:")


def test_phase25k_boardroom_session_commits_to_business_container_artifact():
    record = commit_boardroom_session_artifact(
        business_id="home-fixed",
        session_id="session_001",
        session_type="business_assessment",
        business_context_packet={"business_name": "Home Fixed"},
        department_intelligence_packet={"marketing": {"status": "plan_ready"}},
        department_context_packet={"marketing": {"campaign": "Facebook campaign next week"}},
        user_added_context=[{"text": "Facebook campaign next week"}],
        council_members=["AION", "Gemma", "OpenAI"],
    )

    assert record["target"]["business_container_id"] == "home-fixed"
    assert record["target"]["sub_container"] == "pilot"
    assert record["target"]["artifact_type"] == "boardroom_session"
    assert record["storage_path"].startswith("business_containers/home-fixed/pilot/")
    assert record["storage_state"] == "committed_to_business_container"
    assert record["session_vfs_only"] is False
    assert record["live_side_effects_enabled"] is False
    assert record["boardroom_session_state"] == "business_container_bound"
    assert record["record_valid"] is True
    assert record["merkle_triad_valid"] is True
    assert record["replay_locator_hash"].startswith("sha256:")
    assert record["boardroom_session_record_hash"].startswith("sha256:")


def test_phase25k_file_cabinet_pointer_is_index_only_not_truth():
    record = commit_boardroom_session_artifact(
        business_id="home-fixed",
        session_id="session_002",
        session_type="growth_plan",
        business_context_packet={"business_name": "Home Fixed"},
    )

    pointer = create_file_cabinet_pointer_for_boardroom_session(record)

    assert pointer["type"] == "business_container_artifact"
    assert pointer["document_type"] == "boardroom_session"
    assert pointer["source_of_truth"] == "business_container"
    assert pointer["file_cabinet_role"] == "index_pointer_only"
    assert pointer["target"]["business_container_id"] == "home-fixed"
    assert pointer["target"]["sub_container"] == "pilot"
    assert pointer["target"]["artifact_type"] == "boardroom_session"
    assert pointer["target"]["storage_path"].startswith("business_containers/home-fixed/pilot/")
    assert pointer["pointer_hash"].startswith("sha256:")


def test_boardroom_session_writes_complete_packet_when_platform_root_is_supplied(tmp_path):
    payload = create_boardroom_session_payload(
        business_id="home-fixed",
        session_id="session_persisted",
        session_type="business_assessment",
        business_context_packet={"lines": ["Business name: Home Fixed"]},
        council_members=["OpenAI", "Gemini / Google"],
    )
    payload["boardroom_council_result"] = {
        "consensus": {"summary": "Proceed with an approval-gated plan."}
    }

    record = commit_boardroom_session_artifact(
        business_id="home-fixed",
        session_id="session_persisted",
        session_type="business_assessment",
        full_session_payload=payload,
        platform_root=tmp_path,
    )

    destination = __import__("pathlib").Path(record["persisted_path"])
    assert record["persisted"] is True
    assert destination.is_file()
    assert json.loads(destination.read_text(encoding="utf-8")) == payload
