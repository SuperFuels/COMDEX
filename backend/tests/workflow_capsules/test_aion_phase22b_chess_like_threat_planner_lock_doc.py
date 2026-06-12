from pathlib import Path


def test_phase22b_chess_like_threat_planner_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b_chess_like_threat_planner_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B: Chess-Like Threat Planner Lock" in text
    assert "knight\\_fork" in text
    assert "bait\\_reward" in text
    assert "mate\\_in\\_six" in text
    assert "king\\_safety" in text
    assert "long\\_horizon\\_risk" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B-CHESS-LIKE-THREAT-PLANNER-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
