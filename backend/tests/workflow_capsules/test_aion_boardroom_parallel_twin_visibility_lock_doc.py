from pathlib import Path

DOC = Path("docs/rfc/aion_boardroom_parallel_twin_visibility_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_boardroom_parallel_twin_lock_doc_exists():
    assert DOC.exists()
    assert "Boardroom Parallel Twin Visibility" in _text()


def test_boardroom_parallel_twin_lock_doc_lists_required_panels():
    text = _text()
    for term in [
        "Parallel Twin",
        "Machine Catalog",
        "Machine Cart",
        "Quote Preview",
        "FulfilmentJob",
        "Evidence",
        "Settlement Readiness",
        "Proof Receipt",
        "Proof Verification",
        "Exception Recovery",
        "Machine Trace",
        "Home Fixed",
    ]:
        assert term in text


def test_boardroom_parallel_twin_lock_doc_states_machine_trace_alignment():
    text = _text()
    assert "Machine Trace panel" in text
    assert "external consumer agents" in text
    assert "compact internal A2A view" in text


def test_boardroom_parallel_twin_lock_doc_states_safety_boundary():
    text = _text()
    for term in [
        "MUST NOT",
        "create a live booking",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "send external messages",
        "expose a public A2A route",
    ]:
        assert term in text


def test_boardroom_parallel_twin_lock_doc_states_no_execute_button():
    text = _text()
    assert "No live execute button" in text
    assert "guarded approval path" in text


def test_boardroom_parallel_twin_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
