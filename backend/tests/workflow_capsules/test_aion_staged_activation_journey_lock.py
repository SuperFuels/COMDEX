from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def test_first_board_meeting_is_a_baseline_not_a_completeness_gate():
    text = APP.read_text(encoding="utf-8")
    assert '"baseline_first_meeting"' in text
    assert "Deliver useful value from the evidence available now" in text
    assert "Missing information must become optional routed tasks, not a long interrogation" in text
    assert "First Board meeting · baseline assessment" in text
    assert "A complete company profile is not required today" in text


def test_baseline_board_questions_are_bounded_and_next_meeting_is_schedulable():
    text = APP.read_text(encoding="utf-8")
    assert "baselineMeeting.completed.v1" in text
    assert "baselineMeeting ? 3 : 8" in text
    assert "data-aion-next-board-meeting-date" in text
    assert "data-aion-save-next-board-meeting" in text


def test_department_discovery_is_a_short_explicit_pass():
    text = APP.read_text(encoding="utf-8")
    assert "DISCOVERY_PASS_LIMIT_O18AD = 3" in text
    assert "Short discovery pass complete" in text
    assert "data-aion-o18aa-finish-pass" in text
    assert "data-aion-o18aa-continue-pass" in text
    assert "data-aion-o18aa-request-executive-review" in text
