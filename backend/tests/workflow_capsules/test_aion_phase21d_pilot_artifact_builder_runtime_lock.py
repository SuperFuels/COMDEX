import tempfile
from pathlib import Path

import pytest

from backend.services.aion_mission_mode.pilot_artifact_builder_runtime import (
    PilotArtifactBuilderRuntime,
    PilotArtifactBuilderViolation,
)


def _contract(artifact_type="pdf", artifact_name="home_fixed_quote.pdf"):
    return PilotArtifactBuilderRuntime.build_artifact_contract(
        business_id="home-fixed",
        mission_id="mission-21d",
        mission_run_id="run-001",
        step_id="step-artifact",
        artifact_type=artifact_type,
        artifact_name=artifact_name,
    )


def test_phase21d_contract_blocks_unsupported_artifact_type():
    with pytest.raises(PilotArtifactBuilderViolation):
        PilotArtifactBuilderRuntime.build_artifact_contract(
            business_id="home-fixed",
            mission_id="m",
            mission_run_id="r",
            step_id="s",
            artifact_type="exe",
            artifact_name="bad.exe",
        )


def test_phase21d_contract_blocks_path_traversal_names():
    with pytest.raises(PilotArtifactBuilderViolation):
        _contract(artifact_name="../escape.pdf")


def test_phase21d_artifact_path_is_inside_business_container():
    with tempfile.TemporaryDirectory() as tmp:
        contract = _contract()
        card = PilotArtifactBuilderRuntime.create_draft_artifact(
            container_root=tmp,
            contract=contract,
            title="Home Fixed Draft PDF",
            content="Example quote data",
        )

        rel = card["business_container_relative_path"]
        assert rel.startswith("business/home-fixed/missions/mission-21d/runs/run-001/artifacts/")
        assert Path(tmp, rel).exists()


def test_phase21d_artifact_receipt_is_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        contract = _contract()
        card1 = PilotArtifactBuilderRuntime.create_draft_artifact(
            container_root=tmp,
            contract=contract,
            title="Home Fixed Draft PDF",
            content="Example quote data",
        )
        card2 = PilotArtifactBuilderRuntime.create_draft_artifact(
            container_root=tmp,
            contract=contract,
            title="Home Fixed Draft PDF",
            content="Example quote data",
        )

        assert card1["artifact_hash"] == card2["artifact_hash"]
        assert card1["artifact_receipt_hash"] == card2["artifact_receipt_hash"]


def test_phase21d_artifact_card_is_cockpit_visible():
    with tempfile.TemporaryDirectory() as tmp:
        card = PilotArtifactBuilderRuntime.create_draft_artifact(
            container_root=tmp,
            contract=_contract(),
            title="Home Fixed Draft PDF",
            content="Visible artifact",
        )

        assert card["visible_in_cockpit"] is True
        assert card["status"] == "draft_preview"
        assert card["artifact_hash"].startswith("sha256:")
        assert card["artifact_receipt_hash"].startswith("sha256:")


def test_phase21d_receipt_blocks_live_external_side_effects():
    with tempfile.TemporaryDirectory() as tmp:
        card = PilotArtifactBuilderRuntime.create_draft_artifact(
            container_root=tmp,
            contract=_contract(),
            title="Safe Draft",
            content="No live side effects",
        )

        receipt = card["receipt"]
        assert receipt["live_external_side_effects"] == []
        assert "payment" in receipt["blocked_actions"]
        assert "deploy_site" in receipt["blocked_actions"]
        assert "send_email" in receipt["blocked_actions"]


def test_phase21d_revision_changes_draft_hash_not_silent_overwrite():
    with tempfile.TemporaryDirectory() as tmp:
        contract = _contract()
        first = PilotArtifactBuilderRuntime.create_draft_artifact(
            container_root=tmp,
            contract=contract,
            title="Draft",
            content="Version one",
        )
        revised = PilotArtifactBuilderRuntime.revise_draft_artifact(
            container_root=tmp,
            previous_card=first,
            contract=contract,
            title="Draft",
            revised_content="Version two",
            revision_note="User asked for a clearer draft.",
        )

        assert revised["revision"]["previous_artifact_hash"] == first["artifact_hash"]
        assert revised["revision"]["new_artifact_hash"] == revised["artifact_hash"]
        assert revised["artifact_hash"] != first["artifact_hash"]
        assert revised["revision"]["live_memory_mutated"] is False


def test_phase21d_feedback_is_governed_event_only():
    event = PilotArtifactBuilderRuntime.capture_feedback_event(
        business_id="home-fixed",
        mission_id="mission-21d",
        mission_run_id="run-001",
        step_id="step-artifact",
        artifact_hash="sha256:abc",
        feedback_type="revise",
        feedback_text="Make it shorter.",
    )

    assert event["feedback_event_hash"].startswith("sha256:")
    assert event["live_memory_mutated"] is False
    assert event["template_mutated"] is False
    assert event["provider_state_mutated"] is False
    assert event["reputation_mutated"] is False
    assert event["requires_governed_followup"] is True


def test_phase21d_invalid_feedback_type_blocked():
    with pytest.raises(PilotArtifactBuilderViolation):
        PilotArtifactBuilderRuntime.capture_feedback_event(
            business_id="home-fixed",
            mission_id="mission-21d",
            mission_run_id="run-001",
            step_id="step-artifact",
            artifact_hash="sha256:abc",
            feedback_type="mutate_memory",
            feedback_text="Unsafe",
        )


def test_phase21d_absolute_escape_blocked_by_container_assertion():
    with tempfile.TemporaryDirectory() as tmp:
        escape = Path(tmp).parent / "escape.pdf"
        with pytest.raises(PilotArtifactBuilderViolation):
            PilotArtifactBuilderRuntime._assert_container_path(tmp, escape)
