from pathlib import Path


def test_phase22b22_full_chess_io_interface_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b22_full_chess_io_interface_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.22: Full Chess FEN / UCI / PGN Interface Kernel Lock" in text
    assert "fen\\_input" in text
    assert "fen\\_export" in text
    assert "fen\\_round\\_trip\\_ok" in text
    assert "active\\_color" in text
    assert "castling\\_rights" in text
    assert "en\\_passant\\_target" in text
    assert "halfmove\\_clock" in text
    assert "fullmove\\_number" in text
    assert "uci\\_input" in text
    assert "uci\\_move" in text
    assert "uci\\_round\\_trip\\_ok" in text
    assert "pgn\\_records" in text
    assert "pgn\\_export" in text
    assert "pgn\\_export\\_ok" in text
    assert "io\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B22-FULL-CHESS-IO-INTERFACE-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
