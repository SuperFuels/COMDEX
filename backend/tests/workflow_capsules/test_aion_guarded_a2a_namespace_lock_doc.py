from pathlib import Path

DOC = Path("docs/rfc/aion_guarded_a2a_namespace_lock.tex")

def _text() -> str:
    assert DOC.exists(), "Guarded A2A namespace lock doc must exist"
    return DOC.read_text()

def test_guarded_a2a_namespace_doc_exists():
    text = _text()
    assert "\\section{Phase 11A --- Guarded A2A API Namespace v0}" in text
    assert "AION-GUARDED-A2A-NAMESPACE-v0.1" in text

def test_guarded_a2a_namespace_doc_lists_module_and_functions():
    text = _text()
    assert "backend/modules/aion_gateway/a2a_api.py" in text
    assert "A2AEndpointPreview" in text
    assert "build\\_a2a\\_endpoint\\_preview" in text
    assert "build\\_guarded\\_a2a\\_namespace\\_preview" in text
    assert "build\\_a2a\\_namespace\\_summary" in text

def test_guarded_a2a_namespace_doc_lists_namespace_and_endpoints():
    text = _text()
    assert "/api/aion/a2a/*" in text
    for term in [
        "business\\_capabilities",
        "business\\_machine\\_catalog",
        "business\\_availability",
        "machine\\_cart\\_quote\\_request\\_preview",
        "job\\_request\\_preview",
        "job\\_trace",
        "job\\_evidence",
        "settlement\\_readiness",
        "proof\\_commitment",
        "proof\\_receipt",
        "trust\\_summary",
    ]:
        assert term in text

def test_guarded_a2a_namespace_doc_states_auth_and_determinism():
    text = _text()
    assert "api_key_or_signed_agent_preview" in text
    assert "requires_auth = true" in text
    assert "schema-versioned" in text
    assert "deterministic" in text
    assert "namespace_hash" in text
    assert "response_hash" in text

def test_guarded_a2a_namespace_doc_states_safety():
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
        "Unsupported endpoints MUST be blocked",
    ]:
        assert term in text

def test_guarded_a2a_namespace_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
