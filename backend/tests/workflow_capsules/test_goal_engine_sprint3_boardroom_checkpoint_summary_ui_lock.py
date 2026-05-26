from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_boardroom_ui_references_checkpoint_runtime_summary():
    text = APP.read_text()

    assert "checkpoint_runtime_summary" in text
    assert "goal_engine_checkpoint_runtime_summary" in text


def test_boardroom_ui_has_checkpoint_summary_renderer():
    text = APP.read_text()

    assert "renderAionGoalEngineCheckpointSummaryV1" in text
    assert "getAionGoalEngineCheckpointRuntimeSummaryV1" in text
    assert "Checkpoint / Resume Summary" in text


def test_boardroom_ui_shows_checkpoint_resume_fields():
    text = APP.read_text()

    for label in [
        "Checkpoints",
        "State deltas",
        "Resume blocked",
        "Full payload blocked",
        "Resume requires environment revalidation",
    ]:
        assert label in text


def test_boardroom_ui_shows_checkpoint_previews_and_state_delta_previews():
    text = APP.read_text()

    assert "checkpoint_previews" in text
    assert "state_delta_previews" in text
    assert "loop_context_snapshot" in text
    assert "changed_fields" in text
    assert "would_resume" in text
