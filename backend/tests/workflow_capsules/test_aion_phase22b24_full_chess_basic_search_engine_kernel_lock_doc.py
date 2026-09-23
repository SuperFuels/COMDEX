from pathlib import Path


def test_phase22b24_full_chess_basic_search_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b24_full_chess_basic_search_engine_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.24: Full Chess Basic Search Engine Kernel Lock" in text
    assert "search\\_depth" in text
    assert "candidate\\_move\\_count" in text
    assert "evaluated\\_node\\_count" in text
    assert "rejected\\_move\\_count" in text
    assert "accepted\\_move\\_count" in text
    assert "bad\\_capture\\_rejection\\_count" in text
    assert "king\\_risk\\_rejection\\_count" in text
    assert "material\\_loss\\_rejection\\_count" in text
    assert "selected\\_move\\_id" in text
    assert "selected\\_uci\\_move" in text
    assert "selected\\_move\\_score" in text
    assert "selected\\_move\\_preserves\\_king" in text
    assert "selected\\_move\\_profitable" in text
    assert "search\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B24-FULL-CHESS-BASIC-SEARCH-ENGINE-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
