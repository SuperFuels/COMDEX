from pathlib import Path


def test_phase22b41_live_lichess_game_loop_result_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22b41_full_chess_live_lichess_game_loop_result_recorder_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22B.41: Full Live Lichess Game Loop Result Recorder Kernel Lock" in text
    assert "game_id: cPv6iyKb" in text
    assert "full_id: cPv6iyKbavrO" in text
    assert "account_id: peekoo123" in text
    assert "account_title: BOT" in text
    assert "opponent: Stockfish level 1" in text
    assert "final_status: mate" in text
    assert "winner: white" in text
    assert "aion_result: win" in text
    assert "aion_move_count: 31" in text
    assert "network_move_send_count: 26" in text
    assert "response_ok_count: 26" in text
    assert "did not use an LLM shortcut" in text
    assert "Lock ID: AION-PHASE22B41-FULL-CHESS-LIVE-LICHESS-GAME-LOOP-RESULT-RECORDER-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
