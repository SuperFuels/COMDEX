from pathlib import Path

DOC = Path("docs/rfc/aion_a2a_trust_summary_endpoint_lock.tex")


def _text() -> str:
    assert DOC.exists(), "Phase 11G lock doc must exist"
    return DOC.read_text()


def test_a2a_trust_summary_doc_exists_and_has_lock_id():
    text = _text()
    assert "\\section{Phase 11G --- A2A Trust Summary Endpoint Preview v0}" in text
    assert "AION-A2A-TRUST-SUMMARY-ENDPOINT-v0.1" in text


def test_a2a_trust_summary_doc_lists_endpoint_contract():
    text = _text()
    for term in [
        "aion.a2a_trust_summary_endpoint.v0.1",
        "GET /api/aion/a2a/home_fixed/trust_summary",
        "trust_summary",
        "preview_only = true",
        "guarded = true",
        "requires_auth = true",
        "api_key_or_signed_agent_preview",
        "public_route_exposed = false",
    ]:
        assert term in text


def test_a2a_trust_summary_doc_lists_home_fixed_context():
    text = _text()
    for term in [
        "business_id = home_fixed",
        "business_name = Home Fixed",
        "vertical_key = home_repair",
        "industry_key = trades",
    ]:
        assert term in text


def test_a2a_trust_summary_doc_lists_metrics():
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
        "trust score preview",
        "trust tier preview",
        "explainability notes",
        "human review status",
    ]:
        assert term in text


def test_a2a_trust_summary_doc_blocks_public_ranking():
    text = _text()
    assert "No Public Ranking Boundary" in text
    assert "public_ranking_exposed = false" in text
    assert "no_public_ranking = true" in text
    assert "MUST NOT be used as a public marketplace ranking surface" in text


def test_a2a_trust_summary_doc_lists_hashes():
    text = _text()
    assert "trust\\_summary\\_hash" in text
    assert "response\\_hash" in text
    assert "bundle\\_hash" in text
    assert "summary\\_hash" in text


def test_a2a_trust_summary_doc_states_safety():
    text = _text()
    for term in [
        "expose a public route",
        "expose a public ranking",
        "create a booking",
        "create a live job",
        "execute the Goal Engine",
        "bypass human review",
        "confirm final completion",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "release funds",
        "send external messages",
        "enable live status polling",
    ]:
        assert term in text


def test_a2a_trust_summary_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
