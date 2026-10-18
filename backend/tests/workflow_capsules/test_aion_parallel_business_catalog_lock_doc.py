from pathlib import Path

DOC = Path("docs/rfc/aion_parallel_business_catalog_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_parallel_business_catalog_lock_doc_exists():
    assert DOC.exists()
    assert "AION Parallel Business Catalog v0.1 Lock" in _text()


def test_parallel_business_catalog_lock_doc_names_home_fixed():
    text = _text()
    assert "Home Fixed" in text
    assert "home repair" in text or "home_repair" in text


def test_parallel_business_catalog_lock_doc_lists_core_fields():
    text = _text()
    for term in [
        "protocol\\_version",
        "business\\_id",
        "business\\_name",
        "vertical\\_key",
        "service\\_areas",
        "services",
        "accepted\\_channels",
        "availability\\_summary",
        "proof\\_required",
        "settlement\\_mode",
        "human\\_review\\_required",
        "catalog\\_hash",
    ]:
        assert term in text


def test_parallel_business_catalog_lock_doc_lists_home_fixed_services():
    text = _text()
    for service_key in [
        "general\\_home\\_repair",
        "roof\\_leak\\_repair",
        "painting\\_decorating",
        "pergola\\_canopy\\_repair",
    ]:
        assert service_key in text


def test_parallel_business_catalog_lock_doc_states_hashing_rules():
    text = _text()
    assert "json.dumps" in text
    assert "sort_keys=True" in text
    assert "hashlib.sha256" in text
    assert "Changing service data MUST change" in text


def test_parallel_business_catalog_lock_doc_keeps_safety_boundary():
    text = _text()
    assert "MUST NOT" in text
    assert "create a booking" in text
    assert "create a payment" in text
    assert "create escrow" in text
    assert "expose a public route" in text
    assert "execute the Goal Engine" in text
    assert "move PHO, token, wallet value, or fiat" in text


def test_parallel_business_catalog_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
