from pathlib import Path

DOC = Path("docs/rfc/aion_trust_reputation_summary_lock.tex")

def _text() -> str:
    assert DOC.exists(), "Trust reputation summary lock doc must exist"
    return DOC.read_text()

def test_trust_reputation_doc_exists():
    text = _text()
    assert "\\section{Phase 10A --- Trust and Reputation Summary v0}" in text
    assert "AION-TRUST-REPUTATION-SUMMARY-v0.1" in text

def test_trust_reputation_doc_lists_module_and_functions():
    text = _text()
    assert "backend/modules/aion_gateway/trust_reputation.py" in text
    assert "BusinessTrustSummary" in text
    assert "build\\_business\\_trust\\_summary" in text
    assert "build\\_home\\_fixed\\_trust\\_summary\\_fixture" in text

def test_trust_reputation_doc_lists_tracked_fields():
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
    ]:
        assert term in text

def test_trust_reputation_doc_mentions_home_fixed():
    text = _text()
    assert "Home Fixed" in text
    assert "home_fixed" in text
    assert "home_repair" in text

def test_trust_reputation_doc_states_hash_contract():
    text = _text()
    assert "trust\\_summary\\_hash" in text
    assert "deterministic" in text
    assert "Changing job history MUST change" in text

def test_trust_reputation_doc_states_safety():
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
        "visibility-only",
    ]:
        assert term in text

def test_trust_reputation_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
