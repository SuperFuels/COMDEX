from pathlib import Path


DOC = Path("docs/rfc/aion_phase13_no_booking_side_effect_regression_lock.tex")


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_phase13_no_booking_doc_exists():
    assert DOC.exists()


def test_phase13_no_booking_doc_names_phase():
    text = _text()
    assert "Phase 13C" in text
    assert "No-Booking and No-Live-Job Side-Effect Regression v0" in text


def test_phase13_no_booking_doc_lists_forbidden_behaviour():
    text = _text()
    for term in [
        "create a booking",
        "create a live job",
        "dispatch a provider",
        "start a live job",
        "execute the Goal Engine",
        "bypass human review",
        "expose an unauthenticated public write route",
    ]:
        assert term in text


def test_phase13_no_booking_doc_lists_required_flags():
    text = _text()
    for term in [
        "would_create_booking = false",
        "would_create_live_job = false",
        "would_execute_goal_engine = false",
        "human_review_required = true",
        "approval_can_create_booking = false",
        "approval_can_create_live_job = false",
        "approval_can_execute_goal_engine = false",
    ]:
        assert term in text


def test_phase13_no_booking_doc_says_no_frontend_smoke_test():
    text = _text()
    assert "does not create a new frontend visual surface" in text
    assert "No new manual frontend smoke test is required" in text


def test_phase13_no_booking_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
