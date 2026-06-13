from pathlib import Path


def test_phase22b9_full_chess_threat_map_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b9_full_chess_threat_map_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.9: Full Chess Threat Map Kernel Lock" in text
    assert "black\\_attacked\\_squares" in text
    assert "white\\_attacked\\_squares" in text
    assert "white\\_in\\_check" in text
    assert "checking\\_pieces" in text
    assert "legal\\_escape\\_moves" in text
    assert "rejected\\_unsafe\\_moves" in text
    assert "checking\\_counter\\_moves" in text
    assert "threat\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B9-FULL-CHESS-THREAT-MAP-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
