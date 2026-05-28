from pathlib import Path


DOC = Path("docs/rfc/aion_phase13_trace_drift_regression_lock.tex")


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_phase13_trace_drift_doc_exists():
    assert DOC.exists()


def test_phase13_trace_drift_doc_names_phase():
    text = _text()
    assert "Phase 13G" in text
    assert "Trace Drift Regression v0" in text


def test_phase13_trace_drift_doc_lists_hash_terms():
    text = _text()
    for term in [
        "request\\_hash",
        "normalized\\_intent\\_hash",
        "machine\\_cart\\_request\\_hash",
        "review\\_package\\_hash",
        "approval\\_boundary\\_hash",
        "safety\\_hash",
        "response\\_hash",
        "summary\\_hash",
    ]:
        assert term in text


def test_phase13_trace_drift_doc_lists_forbidden_drift_sources():
    text = _text()
    for term in [
        "uuid.uuid4",
        "random.uuid",
        "time.time()",
        "datetime.now()",
        "datetime.utcnow()",
        "secrets.token",
    ]:
        assert term in text


def test_phase13_trace_drift_doc_states_safety_boundary():
    text = _text()
    for term in [
        "preview\\_only = true",
        "human\\_review\\_required = true",
        "would\\_create\\_live\\_job = false",
        "would\\_execute\\_goal\\_engine = false",
        "would\\_move\\_money = false",
        "would\\_create\\_payment = false",
        "would\\_create\\_escrow = false",
        "would\\_release\\_funds = false",
        "would\\_send\\_external\\_messages = false",
        "unauthenticated\\_public\\_write\\_route\\_exposed = false",
    ]:
        assert term in text


def test_phase13_trace_drift_doc_uses_tessaris_footer():
    text = _text()
    assert "Lock ID: AION-PHASE13G-TRACE-DRIFT-REGRESSION-V0" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
