from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_boardroom_ui_references_goal_runtime_summary():
    text = APP.read_text()

    assert "goal_runtime_summary" in text
    assert "goal_engine_goal_runtime_summary" in text


def test_boardroom_ui_shows_goal_runtime_summary_labels():
    text = APP.read_text()

    expected_labels = [
        "Goal Runtime Summary",
        "Active goals",
        "Outcome score",
        "Evidence required",
        "Bounded loops",
        "Experiment variants",
        "Exploration floor",
        "Approval required",
    ]

    for label in expected_labels:
        assert label in text


def test_boardroom_ui_does_not_claim_completed_equals_success():
    text = APP.read_text()

    assert "Completed is not success without evidence" in text
    assert "outcome_success_requires_evidence" in text


def test_boardroom_ui_preserves_a2a_deferred_state():
    text = APP.read_text()

    assert "A2A deferred" in text
    assert "commercial_interface_ready" in text
    assert "agent_ready" in text
