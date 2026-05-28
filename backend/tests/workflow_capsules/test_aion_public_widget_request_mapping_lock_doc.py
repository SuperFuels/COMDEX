from pathlib import Path


DOC = Path("docs/rfc/aion_public_widget_request_mapping_lock.tex")


def _text():
    assert DOC.exists()
    return DOC.read_text()


def test_public_widget_request_mapping_doc_exists():
    text = _text()
    assert "Phase 12C" in text
    assert "Public Website Form/Button/Chat Widget Request Mapping v0" in text


def test_public_widget_request_mapping_doc_lists_module_and_exports():
    text = _text()
    assert "backend/modules/aion_gateway/public_widget_request_mapping.py" in text
    assert "PUBLIC\\_WIDGET\\_REQUEST\\_MAPPING\\_VERSION" in text
    assert "build\\_public\\_widget\\_request\\_mapping\\_preview" in text
    assert "build\\_public\\_widget\\_request\\_mapping\\_summary" in text
    assert "aion.public_widget_request_mapping.v0.1" in text


def test_public_widget_request_mapping_doc_lists_surfaces():
    text = _text()
    assert "website\\_form\\_widget\\_preview" in text
    assert "website\\_button\\_widget\\_preview" in text
    assert "embedded\\_chat\\_widget\\_preview" in text


def test_public_widget_request_mapping_doc_lists_mapping_kinds():
    text = _text()
    assert "human_form_to_normalized_inbound_intent" in text
    assert "button_request_to_machine_cart_request" in text
    assert "chat_request_to_normalized_intent_or_machine_cart_request" in text


def test_public_widget_request_mapping_doc_lists_required_guards():
    text = _text()
    for term in [
        "tenant/business key validation",
        "signed request validation",
        "rate limiting",
        "abuse protection",
        "human review",
    ]:
        assert term in text


def test_public_widget_request_mapping_doc_lists_hashes():
    text = _text()
    for term in [
        "request\\_hash",
        "normalized\\_intent\\_hash",
        "machine\\_cart\\_request\\_hash",
        "response\\_hash",
        "summary\\_hash",
    ]:
        assert term in text


def test_public_widget_request_mapping_doc_says_no_new_frontend_visual():
    text = _text()
    assert "does not create a new frontend visual surface" in text
    assert "no new manual frontend smoke test is required" in text
    assert "Phase 12D will affect frontend-visible widget behaviour" in text


def test_public_widget_request_mapping_doc_states_safety():
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
        "preview_only = true",
    ]:
        assert term in text


def test_public_widget_request_mapping_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
