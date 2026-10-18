from pathlib import Path


def test_phase22b29_full_chess_lichess_bot_bridge_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b29_full_chess_lichess_bot_bridge_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.29: Full Chess Lichess Bot Bridge Kernel Lock" in text
    assert "bridge\\_mode" in text
    assert "challenge\\_event\\_accepted" in text
    assert "game\\_state\\_event\\_accepted" in text
    assert "game\\_id" in text
    assert "bot\\_colour" in text
    assert "side\\_to\\_move" in text
    assert "input\\_fen" in text
    assert "input\\_moves" in text
    assert "selected\\_bestmove" in text
    assert "lichess\\_move\\_payload" in text
    assert "response\\_ready" in text
    assert "should\\_resign" in text
    assert "should\\_offer\\_draw" in text
    assert "event\\_count" in text
    assert "accepted\\_event\\_count" in text
    assert "lichess\\_bridge\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B29-FULL-CHESS-LICHESS-BOT-BRIDGE-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
