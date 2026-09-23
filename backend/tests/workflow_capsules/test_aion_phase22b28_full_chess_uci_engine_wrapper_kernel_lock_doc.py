from pathlib import Path


def test_phase22b28_full_chess_uci_engine_wrapper_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b28_full_chess_uci_engine_wrapper_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.28: Full Chess UCI Engine Wrapper Kernel Lock" in text
    assert "engine\\_name" in text
    assert "engine\\_author" in text
    assert "uci\\_command\\_count" in text
    assert "accepted\\_command\\_count" in text
    assert "emitted\\_uciok" in text
    assert "emitted\\_readyok" in text
    assert "accepted\\_position\\_fen" in text
    assert "accepted\\_go\\_command" in text
    assert "selected\\_bestmove" in text
    assert "emitted\\_bestmove" in text
    assert "uci\\_transcript" in text
    assert "uci\\_stdout\\_lines" in text
    assert "uci\\_wrapper\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B28-FULL-CHESS-UCI-ENGINE-WRAPPER-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
