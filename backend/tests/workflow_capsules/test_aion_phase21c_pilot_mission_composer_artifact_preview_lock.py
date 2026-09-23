import pytest

from backend.services.aion_mission_mode.pilot_mission_composer_artifact_preview import (
    PilotComposerSecurityError,
    PilotMissionComposerArtifactPreview,
)


def _composer():
    return PilotMissionComposerArtifactPreview(
        business_id="home-fixed",
        mission_id="mission_pdf_001",
        mission_run_id="run_001",
    )


def test_phase21c_composer_creates_plan_preview_for_pdf_document():
    mission = _composer().compose_artifact_mission(
        "Build me a PDF document with X data",
        artifact_type="pdf_document",
        output_name="x-data-summary.pdf",
    )

    assert mission["pilot_status"] == "plan_preview_ready"
    assert mission["artifact_type"] == "pdf_document"
    assert mission["business_container_path"].startswith("business/home-fixed/")
    assert mission["live_external_action_buttons_visible"] is False
    assert mission["raw_tool_access_visible"] is False
    assert mission["credentials_visible"] is False
    assert mission["safety_message"] == "AION stopped itself before doing anything risky."
    assert mission["mission_preview_hash"].startswith("sha256:")


def test_phase21c_artifact_preview_record_shows_path_hash_and_status():
    composer = _composer()
    mission = composer.compose_artifact_mission(
        "Build me a PDF document with X data",
        output_name="x-data-summary.pdf",
    )
    artifact = composer.create_artifact_preview_record(mission)

    assert artifact["artifact_type"] == "pdf_document"
    assert artifact["preview_status"] == "draft_preview"
    assert artifact["business_container_path"] == mission["business_container_path"]
    assert artifact["artifact_hash"].startswith("sha256:")
    assert artifact["open_output_enabled"] is True
    assert artifact["download_enabled"] is True
    assert artifact["view_receipt_enabled"] is True


def test_phase21c_artifact_cannot_escape_business_container():
    composer = _composer()
    mission = composer.compose_artifact_mission("Build me a PDF document")
    mission["business_container_path"] = "/tmp/escaped.pdf"

    with pytest.raises(PilotComposerSecurityError):
        composer.create_artifact_preview_record(mission)


def test_phase21c_feedback_is_governed_and_non_mutating():
    composer = _composer()
    mission = composer.compose_artifact_mission("Build me a PDF document")
    artifact = composer.create_artifact_preview_record(mission)

    feedback = composer.create_feedback_event(
        artifact,
        feedback_action="revise",
        feedback_text="Make it shorter and add a table.",
    )

    assert feedback["governed_feedback_event"] is True
    assert feedback["mutates_live_memory"] is False
    assert feedback["mutates_reusable_template"] is False
    assert feedback["mutates_provider_state"] is False
    assert feedback["mutates_reputation"] is False
    assert feedback["feedback_event_hash"].startswith("sha256:")


def test_phase21c_rejects_unknown_feedback_action():
    composer = _composer()
    mission = composer.compose_artifact_mission("Build me a PDF document")
    artifact = composer.create_artifact_preview_record(mission)

    with pytest.raises(PilotComposerSecurityError):
        composer.create_feedback_event(artifact, feedback_action="silently_save_memory")


def test_phase21c_cockpit_payload_contains_visible_artifact_and_controls():
    composer = _composer()
    mission = composer.compose_artifact_mission("Build me a PDF document with X data")
    artifact = composer.create_artifact_preview_record(mission)
    feedback = composer.create_feedback_event(artifact, feedback_action="approve")

    payload = composer.build_cockpit_payload(mission, artifact, [feedback])

    assert payload["composer_request"] == "Build me a PDF document with X data"
    assert payload["artifact_outputs"][0]["artifact_hash"] == artifact["artifact_hash"]
    assert payload["business_container_files"][0]["path"].startswith("business/home-fixed/")
    assert "open_output" in payload["visible_controls"]
    assert "download_output" in payload["visible_controls"]
    assert "view_receipt" in payload["visible_controls"]
    assert "deploy_now" in payload["hidden_controls"]
    assert payload["live_external_action_buttons_visible"] is False
    assert payload["raw_credentials_visible"] is False
    assert payload["cockpit_payload_hash"].startswith("sha256:")


def test_phase21c_blocks_live_action_request_in_composer():
    with pytest.raises(PilotComposerSecurityError):
        _composer().compose_artifact_mission("Build me a PDF and send email now")


def test_phase21c_hashes_are_deterministic():
    composer = _composer()

    a = composer.compose_artifact_mission("Build me a PDF document with X data")
    b = composer.compose_artifact_mission("Build me a PDF document with X data")

    assert a["mission_preview_hash"] == b["mission_preview_hash"]


def test_phase21c_output_name_is_sanitised():
    mission = _composer().compose_artifact_mission(
        "Build me a PDF document",
        output_name="../escape.pdf",
    )

    assert ".." not in mission["output_name"]
    assert "/" not in mission["output_name"]
    assert mission["business_container_path"].startswith("business/home-fixed/")


def test_phase21c_required_panel_data_is_present():
    composer = _composer()
    mission = composer.compose_artifact_mission("Build me a PDF document")
    artifact = composer.create_artifact_preview_record(mission)
    payload = composer.build_cockpit_payload(mission, artifact)

    assert payload["plan_preview"]
    assert payload["artifact_outputs"]
    assert payload["business_container_files"]
    assert payload["safety_message"] == "AION stopped itself before doing anything risky."
