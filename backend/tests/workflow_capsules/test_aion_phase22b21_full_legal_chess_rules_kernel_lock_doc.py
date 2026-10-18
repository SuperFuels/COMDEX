from pathlib import Path


def test_phase22b21_full_legal_chess_rules_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b21_full_legal_chess_rules_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.21: Full Legal Chess Rules Kernel Lock" in text
    assert "legal\\_rule\\_case\\_count" in text
    assert "passed\\_rule\\_case\\_count" in text
    assert "failed\\_rule\\_case\\_count" in text
    assert "castling\\_validated" in text
    assert "en\\_passant\\_validated" in text
    assert "promotion\\_validated" in text
    assert "checkmate\\_validated" in text
    assert "stalemate\\_validated" in text
    assert "repetition\\_draw\\_validated" in text
    assert "fifty\\_move\\_draw\\_validated" in text
    assert "legal\\_check\\_escape\\_validated" in text
    assert "illegal\\_king\\_adjacency\\_rejected" in text
    assert "full\\_legal\\_rules\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B21-FULL-LEGAL-CHESS-RULES-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
