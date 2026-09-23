from pathlib import Path

DOC = Path("docs/rfc/aion_a2a_handshake_preview_lock.tex")


def _text() -> str:
    assert DOC.exists(), "Phase 11I lock doc must exist"
    return DOC.read_text()


def test_a2a_handshake_doc_exists_and_has_lock_id():
    text = _text()
    assert "\\section{Phase 11I --- Real A2A Handshake Preview v0}" in text
    assert "AION-A2A-HANDSHAKE-PREVIEW-v0.1" in text


def test_a2a_handshake_doc_lists_module_and_exports():
    text = _text()
    assert "backend/modules/aion_gateway/a2a_handshake_preview.py" in text
    for term in [
        "A2A\\_HANDSHAKE\\_PREVIEW\\_VERSION",
        "build\\_a2a\\_handshake\\_preview",
        "build\\_a2a\\_quote\\_negotiation\\_preview",
        "build\\_a2a\\_live\\_status\\_polling\\_preview",
        "build\\_a2a\\_handshake\\_preview\\_bundle",
        "build\\_a2a\\_handshake\\_preview\\_summary",
    ]:
        assert term in text


def test_a2a_handshake_doc_lists_universal_boundary():
    text = _text()
    assert "universal" in text
    assert "MUST NOT be hardcoded as a trade-only system" in text
    assert "legal services" in text
    assert "accounting services" in text
    assert "ecommerce" in text
    assert "B2B suppliers" in text


def test_a2a_handshake_doc_lists_handshake_contract():
    text = _text()
    for term in [
        "requesting_agent_id",
        "requesting_agent_name",
        "requested_protocol",
        "intent_type",
        "status = handshake_preview_only",
        "handshake_accepted = false",
        "agent_identity_validation_enabled = false",
        "scoped_permissions_enabled = false",
    ]:
        assert term in text


def test_a2a_handshake_doc_lists_quote_negotiation_preview():
    text = _text()
    for term in [
        "status = quote_negotiation_preview_only",
        "quote_negotiation_enabled = false",
        "counter_offer_enabled = false",
        "final_quote_created = false",
        "pricing_mode = requires_human_review",
        "future_guarded_approval_path",
    ]:
        assert term in text


def test_a2a_handshake_doc_lists_live_status_polling_preview():
    text = _text()
    for term in [
        "status = live_status_polling_preview_only",
        "current_stage = waiting_human_review",
        "live_status_polling_enabled = false",
        "public_status_stream_enabled = false",
    ]:
        assert term in text


def test_a2a_handshake_doc_lists_hashes():
    text = _text()
    for term in [
        "handshake_hash",
        "quote_negotiation_hash",
        "status_polling_hash",
        "bundle_hash",
        "summary_hash",
    ]:
        assert term in text


def test_a2a_handshake_doc_states_safety():
    text = _text()
    for term in [
        "expose a public route",
        "accept a real A2A handshake",
        "validate live external agent identity",
        "grant scoped permissions",
        "negotiate a live quote",
        "enable live status polling",
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
    ]:
        assert term in text


def test_a2a_handshake_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
