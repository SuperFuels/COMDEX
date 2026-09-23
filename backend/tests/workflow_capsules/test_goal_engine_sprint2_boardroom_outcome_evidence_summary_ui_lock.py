from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_boardroom_ui_has_outcome_evidence_summary_renderer():
    text = APP.read_text()

    assert "renderAionGoalEngineOutcomeEvidenceSummaryV1" in text
    assert "getAionGoalEngineOutcomeEvidenceSummaryV1" in text
    assert "Outcome Evidence Summary" in text


def test_boardroom_ui_reads_outcome_evidence_summary_from_runtime_summary():
    text = APP.read_text()

    assert "goal_runtime_summary" in text
    assert "outcome_evidence_summary" in text
    assert "blocked_outcome_count" in text
    assert "supported_success_count" in text
    assert "outcome_count" in text


def test_boardroom_ui_shows_missing_evidence_warning_and_blocked_reason():
    text = APP.read_text()

    assert "Missing evidence" in text
    assert "outcome_success_requires_evidence" in text
    assert "Completed is not success without evidence" in text


def test_boardroom_runtime_summary_panel_calls_outcome_evidence_renderer():
    text = APP.read_text()

    assert "${renderAionGoalEngineOutcomeEvidenceSummaryV1(summary)}" in text
