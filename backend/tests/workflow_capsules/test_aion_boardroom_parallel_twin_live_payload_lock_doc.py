from __future__ import annotations

from pathlib import Path


DOC = Path("docs/rfc/aion_boardroom_parallel_twin_live_payload_lock.tex")


def _text() -> str:
    assert DOC.exists()
    return DOC.read_text()


def test_boardroom_parallel_twin_live_payload_doc_exists():
    text = _text()
    assert "Phase 9B" in text
    assert "Boardroom Parallel Twin Live Payload Wiring v0" in text


def test_boardroom_parallel_twin_live_payload_doc_lists_module():
    text = _text()
    assert "backend/modules/aion_gateway/boardroom_parallel_twin_payload.py" in text
    assert "build\\_boardroom\\_parallel\\_twin\\_payload" in text
    assert "build\\_boardroom\\_parallel\\_twin\\_summary" in text


def test_boardroom_parallel_twin_live_payload_doc_lists_sections():
    text = _text()
    for term in [
        "machine\\_catalog",
        "machine\\_cart",
        "quote\\_preview",
        "fulfilment\\_job\\_preview",
        "settlement\\_readiness",
        "proof\\_receipt",
        "exception\\_recovery",
        "machine\\_trace\\_preview",
        "payload\\_hash",
    ]:
        assert term in text


def test_boardroom_parallel_twin_live_payload_doc_mentions_home_fixed():
    text = _text()
    assert "Home Fixed" in text
    assert "home_fixed" in text
    assert "home_repair" in text


def test_boardroom_parallel_twin_live_payload_doc_states_safety():
    text = _text()
    for term in [
        "visibility\\_only = true",
        "human\\_review\\_required = true",
        "autonomous\\_execution\\_allowed = false",
        "would\\_execute\\_workflow = false",
        "would\\_create\\_booking = false",
        "would\\_move\\_money = false",
        "would\\_require\\_wallet = false",
        "would\\_create\\_payment = false",
        "would\\_create\\_escrow = false",
        "public\\_a2a\\_route\\_exposed = false",
    ]:
        assert term in text


def test_boardroom_parallel_twin_live_payload_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
