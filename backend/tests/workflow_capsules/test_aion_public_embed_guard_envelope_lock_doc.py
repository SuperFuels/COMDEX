from pathlib import Path

DOC = Path("docs/rfc/aion_public_embed_guard_envelope_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_public_embed_guard_envelope_doc_exists():
    assert DOC.exists()


def test_public_embed_guard_envelope_doc_names_phase():
    text = _text()
    assert "Phase 12E --- Public Embed Widget Guard Envelope v0" in text
    assert "aion.public_embed_guard_envelope.v0.1" in text


def test_public_embed_guard_envelope_doc_lists_module_and_exports():
    text = _text()
    for term in [
        "backend/modules/aion_gateway/public_embed_guard_envelope.py",
        "PUBLIC\\_EMBED\\_GUARD\\_ENVELOPE\\_VERSION",
        "SUPPORTED\\_WIDGET\\_SOURCES",
        "build\\_public\\_embed\\_guard\\_envelope\\_preview",
        "build\\_public\\_embed\\_guard\\_envelope\\_summary",
    ]:
        assert term in text


def test_public_embed_guard_envelope_doc_lists_supported_widget_sources():
    text = _text()
    for term in [
        "website\\_form\\_widget",
        "website\\_button\\_widget",
        "embedded\\_chat\\_widget",
        "unsupported_widget_source",
    ]:
        assert term in text


def test_public_embed_guard_envelope_doc_lists_required_guards():
    text = _text()
    for term in [
        "tenant/business key validation",
        "signed request validation",
        "rate limiting",
        "abuse protection",
        "human review",
        "tenant_business_key_validation_required = true",
        "signed_request_validation_required = true",
        "rate_limiting_required = true",
        "abuse_protection_required = true",
        "human_review_required = true",
    ]:
        assert term in text


def test_public_embed_guard_envelope_doc_lists_hashes():
    text = _text()
    for term in [
        "request\\_hash",
        "guard\\_hash",
        "safety\\_hash",
        "response\\_hash",
        "summary\\_hash",
    ]:
        assert term in text


def test_public_embed_guard_envelope_doc_says_no_new_frontend_visual():
    text = _text()
    assert "does not create a new frontend visual surface" in text
    assert "No new manual frontend smoke test is required" in text


def test_public_embed_guard_envelope_doc_states_safety():
    text = _text()
    for term in [
        "preview_only = true",
        "human_review_required = true",
        "would_create_booking = false",
        "would_create_live_job = false",
        "would_execute_goal_engine = false",
        "would_move_money = false",
        "would_create_payment = false",
        "would_create_escrow = false",
        "would_release_funds = false",
        "would_send_external_messages = false",
        "unauthenticated_public_write_route_exposed = false",
        "public_route_mounted = false",
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
        "mount a public write route",
    ]:
        assert term in text


def test_public_embed_guard_envelope_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
