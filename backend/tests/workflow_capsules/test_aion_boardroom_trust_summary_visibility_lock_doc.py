from pathlib import Path

DOC = Path("docs/rfc/aion_boardroom_trust_summary_visibility_lock.tex")

def _text() -> str:
    assert DOC.exists(), "Boardroom trust summary visibility lock doc must exist"
    return DOC.read_text()

def test_boardroom_trust_summary_doc_exists():
    text = _text()
    assert "\\section{Phase 10B --- Boardroom Trust Summary Visibility v0}" in text
    assert "AION-BOARDROOM-TRUST-SUMMARY-VISIBILITY-v0.1" in text

def test_boardroom_trust_summary_doc_lists_surface():
    text = _text()
    assert "desktop/mac/src/app.js" in text
    assert "installBoardroomTrustSummaryVisibilityV0" in text
    assert "renderBoardroomTrustSummaryVisibilityV0" in text
    assert "window.renderBoardroomTrustSummaryVisibilityV0" in text
    assert "boardroom-trust-summary-visibility-v0" in text

def test_boardroom_trust_summary_doc_lists_rendered_fields():
    text = _text()
    for term in [
        "verified completed jobs",
        "disputed jobs",
        "cancelled jobs",
        "failed jobs",
        "average response time",
        "average completion time",
        "evidence-backed completion rate",
        "proof commitment rate",
        "proof verification success rate",
        "quote reliability rate",
        "recovery success rate",
        "trust\\_summary\\_hash",
        "explainability notes",
        "human review status",
    ]:
        assert term in text

def test_boardroom_trust_summary_doc_mentions_home_fixed():
    text = _text()
    assert "Home Fixed" in text
    assert "home_fixed" in text
    assert "home_repair" in text

def test_boardroom_trust_summary_doc_states_safety():
    text = _text()
    for term in [
        "create a booking",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "send external messages",
        "public A2A route",
        "public ranking",
        "visibility_only = true",
        "no_public_ranking = true",
    ]:
        assert term in text

def test_boardroom_trust_summary_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
