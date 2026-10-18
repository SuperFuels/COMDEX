from pathlib import Path


SERVICE = Path("backend/modules/aion_business/runtime/business_container_service.py")


def test_boardroom_payload_includes_goal_engine_runtime_preview_key():
    text = SERVICE.read_text()

    assert "goal_engine_preview_bundle" in text
    assert "goal_runtime_summary" in text
    assert "checkpoint_runtime_summary" in text
    assert "resume_revalidation_summary" in text
    assert "experiment_runtime_summary" in text
    assert "orchestrator_runtime_summary" in text
    assert "goal_decomposition_runtime_summary" in text


def test_boardroom_payload_uses_goal_engine_runtime_preview_block():
    text = SERVICE.read_text()

    assert "goal_engine_runtime_preview" in text
    assert "aion_goal_engine_boardroom_runtime_preview_v1" in text


def test_boardroom_payload_marks_preview_dry_run_only():
    text = SERVICE.read_text()

    assert "\"dry_run_only\": True" in text or "'dry_run_only': True" in text
    assert "\"would_execute\": False" in text or "'would_execute': False" in text
    assert "\"would_write_external\": False" in text or "'would_write_external': False" in text
    assert "\"would_grant_permission\": False" in text or "'would_grant_permission': False" in text
