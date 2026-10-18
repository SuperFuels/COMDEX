from pathlib import Path

DOC = Path("docs/rfc/aion_a2a_well_known_discovery_lock.tex")


def _text() -> str:
    assert DOC.exists(), "docs/rfc/aion_a2a_well_known_discovery_lock.tex must exist"
    return DOC.read_text()


def test_well_known_discovery_doc_exists_and_has_lock_id():
    text = _text()
    assert "\\section{Phase 11H --- Well-Known Discovery Preview v0}" in text
    assert "AION-A2A-WELL-KNOWN-DISCOVERY-v0.1" in text


def test_well_known_discovery_doc_lists_paths():
    text = _text()
    assert "/.well-known/aion-agent" in text
    assert "/.well-known/ai-agent" in text


def test_well_known_discovery_doc_lists_capability_discovery():
    text = _text()
    for term in [
        "business capabilities",
        "machine catalog",
        "availability preview",
        "quote request preview",
        "job request preview",
        "job trace preview",
        "job evidence preview",
        "settlement readiness preview",
        "proof receipt preview",
        "trust summary preview",
    ]:
        assert term in text


def test_well_known_discovery_doc_lists_availability_and_protocols():
    text = _text()
    for term in [
        "status = preview_available",
        "availability_mode = preview_only",
        "live_booking_enabled = false",
        "live_status_polling_enabled = false",
        "aion.a2a.preview.v0",
        "aion.machine_cart.preview.v0",
        "aion.proof_receipt.preview.v0",
        "aion.trust_summary.preview.v0",
    ]:
        assert term in text


def test_well_known_discovery_doc_lists_auth_requirements():
    text = _text()
    for term in [
        "requires_auth = true",
        "auth_mode = api_key_or_signed_agent_preview",
        "api_key_supported_preview = true",
        "signed_agent_supported_preview = true",
        "agent_identity_validation_enabled = false",
        "scoped_permissions_enabled = false",
    ]:
        assert term in text


def test_well_known_discovery_doc_mentions_universal_verticals():
    text = _text()
    assert "universal" in text
    assert "legal services" in text
    assert "accounting services" in text
    assert "ecommerce" in text
    assert "B2B suppliers" in text


def test_well_known_discovery_doc_lists_hashes():
    text = _text()
    assert "discovery_hash" in text
    assert "response_hash" in text
    assert "summary_hash" in text


def test_well_known_discovery_doc_states_safety():
    text = _text()
    for term in [
        "expose a public route",
        "mount \\texttt{/.well-known/aion-agent}",
        "mount \\texttt{/.well-known/ai-agent}",
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
        "enable live status polling",
        "public_route_mounted = false",
    ]:
        assert term in text


def test_well_known_discovery_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
