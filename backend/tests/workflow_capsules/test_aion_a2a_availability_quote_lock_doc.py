from pathlib import Path

DOC = Path("docs/rfc/aion_a2a_availability_quote_lock.tex")

def _text() -> str:
    assert DOC.exists(), "A2A availability quote lock doc must exist"
    return DOC.read_text()

def test_a2a_availability_quote_doc_exists():
    text = _text()
    assert "\\section{Phase 11C --- A2A Availability and Quote Request Preview v0}" in text
    assert "AION-A2A-AVAILABILITY-QUOTE-v0.1" in text

def test_a2a_availability_quote_doc_lists_module_and_functions():
    text = _text()
    assert "backend/modules/aion_gateway/a2a_availability_quote.py" in text
    assert "build\\_business\\_availability\\_preview" in text
    assert "validate\\_machine\\_cart\\_quote\\_request\\_preview" in text
    assert "build\\_machine\\_cart\\_quote\\_request\\_preview" in text
    assert "build\\_a2a\\_availability\\_quote\\_bundle" in text

def test_a2a_availability_quote_doc_lists_endpoints():
    text = _text()
    assert "business\\_availability" in text
    assert "machine\\_cart\\_quote\\_request\\_preview" in text

def test_a2a_availability_quote_doc_lists_universal_boundary():
    text = _text()
    assert "universal Gateway contracts" in text
    assert "This is not a trade-only contract" in text
    assert "legal services" in text
    assert "accounting services" in text
    assert "vertical-specific adapter rules" in text

def test_a2a_availability_quote_doc_lists_request_required_fields():
    text = _text()
    for term in [
        "business\\_id",
        "vertical\\_key",
        "service\\_id",
        "requested\\_outcome",
    ]:
        assert term in text

def test_a2a_availability_quote_doc_lists_quote_boundary():
    text = _text()
    for term in [
        "status = quote_preview_only",
        "final_quote_created = false",
        "quote_negotiation_enabled = false",
        "human_review_required = true",
        "pricing_mode = requires_human_review",
        "future_guarded_approval_path",
    ]:
        assert term in text

def test_a2a_availability_quote_doc_lists_hashes():
    text = _text()
    assert "availability_hash" in text
    assert "quote_request_hash" in text
    assert "bundle_hash" in text

def test_a2a_availability_quote_doc_states_safety():
    text = _text()
    for term in [
        "expose a public route",
        "create a booking",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "send external messages",
        "negotiate a live quote",
    ]:
        assert term in text

def test_a2a_availability_quote_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
