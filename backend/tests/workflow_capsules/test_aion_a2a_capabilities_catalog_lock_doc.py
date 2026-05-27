from pathlib import Path

DOC = Path("docs/rfc/aion_a2a_capabilities_catalog_lock.tex")

def _text() -> str:
    assert DOC.exists(), "A2A capabilities catalog lock doc must exist"
    return DOC.read_text()

def test_a2a_capabilities_catalog_doc_exists():
    text = _text()
    assert "\\section{Phase 11B --- A2A Business Capabilities and Machine Catalog Preview v0}" in text
    assert "AION-A2A-CAPABILITIES-CATALOG-v0.1" in text

def test_a2a_capabilities_catalog_doc_lists_module_and_functions():
    text = _text()
    assert "backend/modules/aion_gateway/a2a_capabilities.py" in text
    assert "build\\_business\\_capabilities\\_preview" in text
    assert "build\\_business\\_machine\\_catalog\\_preview" in text
    assert "build\\_a2a\\_capabilities\\_catalog\\_bundle" in text

def test_a2a_capabilities_catalog_doc_lists_universal_boundary():
    text = _text()
    assert "universal Gateway contracts" in text
    assert "MUST NOT be hardcoded as a trade-only system" in text
    assert "legal services" in text
    assert "accounting services" in text
    assert "vertical adapter" in text

def test_a2a_capabilities_catalog_doc_lists_identity_fields():
    text = _text()
    assert "business_id = home_fixed" in text
    assert "business_name = Home Fixed" in text
    assert "vertical_key = home_repair" in text
    assert "industry_key = trades" in text

def test_a2a_capabilities_catalog_doc_lists_protocols_auth_and_hashes():
    text = _text()
    for term in [
        "aion.a2a.preview.v0",
        "aion.machine_cart.preview.v0",
        "aion.proof_receipt.preview.v0",
        "api_key_or_signed_agent_preview",
        "capabilities_hash",
        "catalog_hash",
        "bundle_hash",
    ]:
        assert term in text

def test_a2a_capabilities_catalog_doc_states_safety():
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
    ]:
        assert term in text

def test_a2a_capabilities_catalog_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
