from pathlib import Path


def test_phase22b30_full_chess_live_lichess_bot_connector_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b30_full_chess_live_lichess_bot_connector_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.30: Full Chess Live Lichess Bot Connector Kernel Lock" in text
    assert "connector\\_mode" in text
    assert "config" in text
    assert "endpoints" in text
    assert "game\\_id" in text
    assert "selected\\_bestmove" in text
    assert "lichess\\_move\\_payload" in text
    assert "would\\_accept\\_challenge" in text
    assert "would\\_post\\_move" in text
    assert "network\\_call\\_performed" in text
    assert "dry\\_run\\_guard\\_active" in text
    assert "token\\_redaction\\_active" in text
    assert "connector\\_ready" in text
    assert "live\\_connector\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Network writes MUST remain disabled by default" in text
    assert "Lock ID: AION-PHASE22B30-FULL-CHESS-LIVE-LICHESS-BOT-CONNECTOR-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
