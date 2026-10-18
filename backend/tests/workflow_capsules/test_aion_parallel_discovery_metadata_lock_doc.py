from pathlib import Path

DOC = Path("docs/rfc/aion_parallel_discovery_metadata_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_parallel_discovery_metadata_lock_doc_exists():
    assert DOC.exists()
    assert "AION Parallel Discovery Metadata v0.1 Lock" in _text()


def test_parallel_discovery_metadata_lock_doc_lists_core_fields():
    text = _text()
    for term in [
        "protocol\\_version",
        "business\\_id",
        "business\\_name",
        "vertical\\_key",
        "accepted\\_protocol\\_versions",
        "endpoints",
        "auth\\_policy",
        "rate\\_limit\\_policy",
        "public\\_route\\_exposed = false",
        "human\\_review\\_required = true",
        "discovery\\_hash",
    ]:
        assert term in text


def test_parallel_discovery_metadata_lock_doc_names_home_fixed():
    text = _text()
    assert "Home Fixed" in text
    assert "business_id = home_fixed" in text
    assert "vertical_key = home_repair" in text


def test_parallel_discovery_metadata_lock_doc_lists_endpoint_placeholders():
    text = _text()
    for term in [
        "discovery",
        "ai\\_agent\\_discovery",
        "catalog",
        "capabilities",
        "quote",
        "trace",
        "proof",
    ]:
        assert term in text


def test_parallel_discovery_metadata_lock_doc_mentions_well_known_routes():
    text = _text()
    assert "/.well-known/aion-agent" in text
    assert "/.well-known/ai-agent" in text


def test_parallel_discovery_metadata_lock_doc_states_hashing_rules():
    text = _text()
    assert "json.dumps" in text
    assert "sort_keys=True" in text
    assert "hashlib.sha256" in text
    assert "Changing the business identity or endpoint metadata MUST change" in text


def test_parallel_discovery_metadata_lock_doc_keeps_safety_boundary():
    text = _text()
    assert "MUST NOT" in text
    assert "expose \\texttt{/.well-known/aion-agent}" in text
    assert "expose \\texttt{/.well-known/ai-agent}" in text
    assert "create a public A2A API" in text
    assert "create a booking" in text
    assert "create a payment" in text
    assert "create escrow" in text
    assert "execute the Goal Engine" in text
    assert "move money" in text
    assert "move PHO" in text
    assert "require a wallet" in text
    assert "grant permissions" in text


def test_parallel_discovery_metadata_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
