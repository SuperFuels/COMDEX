from pathlib import Path


def test_phase22d6_real_level2_sqi_game_loop_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22d6_real_lichess_level2_sqi_game_loop_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22D.6: Full Real Lichess Level 2 SQI Game Loop Kernel Lock" in text
    assert "full real level 2 SQI game loop implemented and tested in dry-run mode" in text
    assert "full_chess_real_lichess_level2_sqi_game_loop_kernel.py" in text
    assert "AION_LICHESS_LIVE=1" in text
    assert "LICHESS_BOT_TOKEN" in text
    assert "Phase 22D.3 live-loop SQI adapter" in text
    assert "Lock ID: AION-PHASE22D6-FULL-REAL-LICHESS-LEVEL2-SQI-GAME-LOOP-KERNEL-LOCK" in text
