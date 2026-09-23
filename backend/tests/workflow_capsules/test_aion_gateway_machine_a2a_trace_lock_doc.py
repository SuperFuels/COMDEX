from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_machine_a2a_trace_lock.tex")


def _text():
    return DOC.read_text()


def test_machine_a2a_trace_lock_doc_exists():
    assert DOC.exists()
    assert "AION Gateway Machine A2A Trace v0.1 Lock" in _text()


def test_machine_a2a_trace_lock_doc_lists_core_fields():
    text = _text()
    for term in [
        "job\\_id",
        "business\\_id",
        "workflow\\_run\\_id",
        "goal\\_id",
        "current\\_stage",
        "next\\_expected\\_event",
        "blocked\\_reason",
        "provider\\_assignment",
        "evidence\\_state",
        "approval\\_state",
        "exception\\_state",
        "settlement\\_readiness\\_state",
        "proof\\_commitment\\_state",
        "machine\\_trace\\_hash",
    ]:
        assert term in text


def test_machine_a2a_trace_lock_doc_states_future_route_not_created_yet():
    text = _text()
    assert "GET /api/aion/a2a/jobs/{job_id}/trace" in text
    assert "does not create that public route yet" in text


def test_machine_a2a_trace_lock_doc_states_hashing_rule():
    text = _text()
    assert "json.dumps" in text
    assert "sort_keys=True" in text
    assert "hashlib.sha256" in text
    assert "MUST be stable across dictionary key ordering" in text


def test_machine_a2a_trace_lock_doc_keeps_safety_boundary():
    text = _text()
    assert "MUST NOT" in text
    assert "expose public routes" in text
    assert "execute workflows" in text
    assert "mutate business containers" in text
    assert "commit to GlyphChain" in text
    assert "grant permissions" in text


def test_machine_a2a_trace_lock_doc_mentions_boardroom_alignment():
    text = _text()
    assert "workflow_run -> Human Boardroom -> Machine A2A trace" in text
    assert "human\\_boardroom\\_alignment" in text


def test_machine_a2a_trace_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
