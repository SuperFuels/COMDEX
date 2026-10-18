from pathlib import Path

DOC = Path("docs/rfc/aion_machine_cart_quote_handshake_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_machine_cart_quote_handshake_lock_doc_exists():
    assert DOC.exists()
    assert "AION Machine Cart and Quote Handshake v0.1 Lock" in _text()


def test_machine_cart_quote_handshake_lock_doc_lists_core_fields():
    text = _text()
    for term in [
        "business\\_id",
        "line\\_items",
        "service\\_key",
        "constraints",
        "location\\_town",
        "requested\\_window",
        "max\\_fiat\\_price\\_minor",
        "currency",
        "required\\_evidence",
        "consumer\\_agent\\_id",
        "cart\\_hash",
    ]:
        assert term in text


def test_machine_cart_quote_handshake_lock_doc_lists_quote_outputs():
    text = _text()
    for term in [
        "quote\\_preview",
        "quote\\_hash",
        "quote\\_lines",
        "evidence\\_required",
        "missing\\_evidence",
        "fulfilment\\_job\\_preview\\_link",
        "settlement\\_readiness\\_preview",
        "proof\\_commitment\\_preview",
        "blocked\\_reasons",
        "warnings",
    ]:
        assert term in text


def test_machine_cart_quote_handshake_lock_doc_names_home_fixed():
    text = _text()
    assert "Home Fixed" in text
    assert "business\\_id = home\\_fixed" in text


def test_machine_cart_quote_handshake_lock_doc_states_hashing_rules():
    text = _text()
    assert "json.dumps" in text
    assert "sort_keys=True" in text
    assert "hashlib.sha256" in text
    assert "Changing the requested service MUST change" in text


def test_machine_cart_quote_handshake_lock_doc_keeps_safety_boundary():
    text = _text()
    assert "MUST NOT" in text
    assert "create a booking" in text
    assert "create a payment" in text
    assert "create escrow" in text
    assert "execute the Goal Engine" in text
    assert "expose a public route" in text
    assert "move money" in text
    assert "move PHO" in text
    assert "require a wallet" in text
    assert "autonomously create a FulfilmentJob" in text


def test_machine_cart_quote_handshake_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
