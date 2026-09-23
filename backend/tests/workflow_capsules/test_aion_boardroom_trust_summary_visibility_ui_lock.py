from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    assert APP.exists(), "desktop/mac/src/app.js must exist"
    return APP.read_text()


def test_boardroom_trust_summary_renderer_exists():
    text = _text()
    assert "installBoardroomTrustSummaryVisibilityV0" in text
    assert "renderBoardroomTrustSummaryVisibilityV0" in text
    assert "window.renderBoardroomTrustSummaryVisibilityV0" in text
    assert "boardroom-trust-summary-visibility-v0" in text


def test_boardroom_trust_summary_mentions_home_fixed_fixture():
    text = _text()
    section_start = text.find("installBoardroomTrustSummaryVisibilityV0")
    assert section_start >= 0
    section = text[section_start:]

    for term in [
        "Home Fixed",
        "home_fixed",
        "home_repair",
        "trust_summary_ready",
    ]:
        assert term in section


def test_boardroom_trust_summary_shows_required_metrics():
    text = _text()
    section_start = text.find("installBoardroomTrustSummaryVisibilityV0")
    assert section_start >= 0
    section = text[section_start:]

    for term in [
        "Verified Completed Jobs",
        "Disputed Jobs",
        "Cancelled Jobs",
        "Failed Jobs",
        "Average Response",
        "Average Completion",
        "Evidence-backed Completion",
        "Proof Commitment",
        "Proof Verification",
        "Quote Reliability",
        "Recovery Success",
        "Trust Summary Hash",
        "Explainability Notes",
    ]:
        assert term in section


def test_boardroom_trust_summary_keeps_visibility_only_boundary():
    text = _text()
    section_start = text.find("installBoardroomTrustSummaryVisibilityV0")
    assert section_start >= 0
    section = text[section_start:]

    for term in [
        "visibility_only",
        "human_review_required",
        "public_a2a_exposed",
        "no_public_ranking",
        "would_create_booking",
        "would_move_money",
        "would_move_pho",
        "would_create_payment",
        "would_create_escrow",
        "would_send_external_message",
    ]:
        assert term in section


def test_boardroom_trust_summary_has_no_live_or_ranking_controls():
    text = _text()
    section_start = text.find("installBoardroomTrustSummaryVisibilityV0")
    assert section_start >= 0
    section = text[section_start:]

    banned = [
        "Execute Now",
        "Run Live",
        "Create Booking",
        "Take Payment",
        "Create Escrow",
        "Send Message",
        "Publish Ranking",
        "Public Rank",
        "Submit Public A2A",
    ]

    for term in banned:
        assert term not in section
