from pathlib import Path


def test_phase22b2_mini_chess_threat_map_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b2_mini_chess_threat_map_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.2: Mini Chess Threat Map Kernel Lock" in text
    assert "attacked\\_squares" in text
    assert "defended\\_pieces" in text
    assert "undefended\\_pieces" in text
    assert "white\\_in\\_check" in text
    assert "legal\\_escape\\_moves" in text
    assert "unsafe\\_captures" in text
    assert "checking\\_moves" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B2-MINI-CHESS-THREAT-MAP-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
