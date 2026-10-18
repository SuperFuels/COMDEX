from pathlib import Path

DOC = Path("docs/rfc/aion_public_intent_gateway_lock.tex")


def _text():
    return DOC.read_text()


def test_public_intent_gateway_doc_exists():
    assert DOC.exists()


def test_public_intent_gateway_doc_names_phase_and_version():
    text = _text()
    assert "Phase 12A --- Public Website Intent Gateway Preview v0" in text
    assert "aion.public_intent_gateway.v0.1" in text
    assert "AION-PUBLIC-INTENT-GATEWAY-v0.1" in text


def test_public_intent_gateway_doc_lists_module_and_exports():
    text = _text()
    assert "backend/modules/aion_gateway/public_intent_gateway.py" in text
    for term in [
        "PUBLIC\\_INTENT\\_GATEWAY\\_VERSION",
        "PublicIntentGatewayRequest",
        "PublicIntentGatewayPreview",
        "build\\_public\\_intent\\_gateway\\_preview",
        "build\\_public\\_intent\\_gateway\\_summary",
    ]:
        assert term in text


def test_public_intent_gateway_doc_lists_input_fields():
    text = _text()
    for term in [
        "business\\_id",
        "tenant\\_key",
        "source",
        "customer\\_name",
        "customer\\_contact",
        "message",
        "location",
        "requested\\_service",
        "preferred\\_window",
        "max\\_fiat\\_price",
        "currency",
    ]:
        assert term in text


def test_public_intent_gateway_doc_lists_form_and_cart_mapping():
    text = _text()
    assert "NormalizedInboundIntent" in text
    assert "MachineCartRequest" in text
    for term in [
        "intent\\_type = public\\_website\\_service\\_enquiry",
        "normalization\\_status = preview\\_only",
        "status = machine\\_cart\\_request\\_preview\\_only",
        "quote_preview_requires_human_review",
    ]:
        assert term in text


def test_public_intent_gateway_doc_lists_required_guards():
    text = _text()
    for term in [
        "tenant/business key validation",
        "signed request validation",
        "rate limiting",
        "abuse protection",
        "human review",
    ]:
        assert term in text


def test_public_intent_gateway_doc_lists_hashes():
    text = _text()
    for term in [
        "request\\_hash",
        "normalized\\_intent\\_hash",
        "machine\\_cart\\_request\\_hash",
        "response\\_hash",
        "summary\\_hash",
    ]:
        assert term in text


def test_public_intent_gateway_doc_states_safety():
    text = _text()
    for term in [
        "create a booking",
        "create a live job",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "release funds",
        "send external messages",
        "expose an unauthenticated public write route",
    ]:
        assert term in text


def test_public_intent_gateway_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
