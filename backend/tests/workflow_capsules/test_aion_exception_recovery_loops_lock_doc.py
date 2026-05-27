from pathlib import Path

DOC = Path("docs/rfc/aion_exception_recovery_loops_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_exception_recovery_lock_doc_exists():
    assert DOC.exists()
    assert "AION Exception and Recovery Loops v0.1 Lock" in _text()


def test_exception_recovery_lock_doc_lists_exception_types():
    text = _text()
    for term in [
        "provider\\_late",
        "provider\\_cancelled",
        "missing\\_evidence",
        "quote\\_changed",
        "budget\\_exceeded",
        "approval\\_delayed",
        "unsafe\\_request\\_blocked",
        "customer\\_dispute",
        "proof\\_verification\\_failed",
        "settlement\\_readiness\\_blocked",
    ]:
        assert term in text


def test_exception_recovery_lock_doc_lists_recovery_actions():
    text = _text()
    for term in [
        "reschedule",
        "backup\\_provider",
        "pause",
        "cancel",
        "escalate",
        "request\\_missing\\_evidence",
        "revise\\_quote",
        "recommend\\_refund",
    ]:
        assert term in text


def test_exception_recovery_lock_doc_lists_core_fields():
    text = _text()
    for term in [
        "exception\\_id",
        "exception\\_type",
        "business\\_id",
        "job\\_id",
        "severity",
        "source",
        "summary",
        "detected\\_at\\_ms",
        "evidence\\_refs",
        "exception\\_hash",
    ]:
        assert term in text


def test_exception_recovery_lock_doc_states_machine_trace_compatibility():
    text = _text()
    assert "build_exception_state_for_machine_trace" in text
    assert "machine\\_trace\\_exception\\_hash" in text


def test_exception_recovery_lock_doc_states_hashing_rules():
    text = _text()
    assert "json.dumps" in text
    assert "sort_keys=True" in text
    assert "hashlib.sha256" in text
    assert "Changing exception content MUST change" in text


def test_exception_recovery_lock_doc_states_safety_boundary():
    text = _text()
    for term in [
        "execute a workflow",
        "create a booking",
        "create a payment",
        "create escrow",
        "move money",
        "move PHO",
        "require a token",
        "require a wallet",
        "send an email",
        "send a WhatsApp message",
        "call a phone provider",
        "expose a public route",
        "autonomously resolve an exception",
    ]:
        assert term in text


def test_exception_recovery_lock_doc_mentions_home_fixed():
    text = _text()
    assert "business_id = home_fixed" in text
    assert "vertical_key = home_repair" in text
    assert "Home Fixed" in text


def test_exception_recovery_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
