from pathlib import Path


def test_phase22b6_mini_chess_full_loop_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b6_mini_chess_full_loop_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.6: Mini Chess Full Loop Lock" in text
    assert "legal\\_move\\_lock\\_passed" in text
    assert "threat\\_map\\_lock\\_passed" in text
    assert "capture\\_material\\_lock\\_passed" in text
    assert "self\\_play\\_lock\\_passed" in text
    assert "opponent\\_win\\_lock\\_passed" in text
    assert "full\\_loop\\_passed" in text
    assert "combined\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B6-MINI-CHESS-FULL-LOOP-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
