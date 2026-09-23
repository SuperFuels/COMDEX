from pathlib import Path


def test_phase22b38_full_chess_lichess_dry_run_game_replay_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b38_full_chess_lichess_dry_run_game_replay_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.38: Full Chess Lichess Dry-Run Game Replay Kernel Lock" in text
    assert "replay\\_mode" in text
    assert "dry\\_run" in text
    assert "network\\_call\\_performed" in text
    assert "human\\_approval\\_required" in text
    assert "event\\_count" in text
    assert "replayed\\_event\\_count" in text
    assert "game\\_id" in text
    assert "aion\\_colour" in text
    assert "aion\\_turn\\_detected" in text
    assert "selected\\_bestmove" in text
    assert "selected\\_policy" in text
    assert "prepared\\_move\\_url" in text
    assert "would\\_post\\_move" in text
    assert "replay\\_events" in text
    assert "replay\\_decision" in text
    assert "dry\\_run\\_replay\\_trace\\_hash" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE22B38-FULL-CHESS-LICHESS-DRY-RUN-GAME-REPLAY-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
