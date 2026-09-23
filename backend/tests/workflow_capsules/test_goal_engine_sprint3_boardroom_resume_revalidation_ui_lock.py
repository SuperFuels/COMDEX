from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_boardroom_ui_references_resume_revalidation_summary():
    text = APP.read_text()

    assert "resume_revalidation_summary" in text
    assert "goal_engine_resume_revalidation_summary" in text


def test_boardroom_ui_has_resume_revalidation_renderer():
    text = APP.read_text()

    assert "renderAionGoalEngineResumeRevalidationSummaryV1" in text
    assert "getAionGoalEngineResumeRevalidationSummaryV1" in text
    assert "Resume Revalidation Summary" in text


def test_boardroom_ui_shows_resume_revalidation_fields():
    text = APP.read_text()

    for label in [
        "Revalidations",
        "Resume allowed",
        "Resume blocked",
        "Safe stop required",
        "External state changed",
        "Approval not valid",
        "Vault not ready",
        "Connectors not ready",
        "Parent goal no longer required",
    ]:
        assert label in text


def test_boardroom_ui_shows_revalidation_previews_and_suggested_action():
    text = APP.read_text()

    assert "revalidation_previews" in text
    assert "suggested_next_action" in text
    assert "stop_or_replan_before_resume" in text
    assert "would_resume" in text
