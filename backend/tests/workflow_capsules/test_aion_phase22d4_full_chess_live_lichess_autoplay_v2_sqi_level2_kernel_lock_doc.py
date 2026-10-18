from pathlib import Path


def test_phase22d4_live_lichess_autoplay_v2_sqi_level2_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22d4_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22D.4: Full Chess Live Lichess Autoplay v2 SQI Level 2 Kernel Lock" in text
    assert "guarded SQI autoplay v2 level 2 path implemented and tested" in text
    assert "full_chess_live_lichess_autoplay_v2_sqi_level2_kernel.py" in text
    assert "target Lichess Stockfish level 2" in text
    assert "Phase 22D.3 live-loop SQI adapter" in text
    assert "Phase 22D.2 SQI-guided selection" in text
    assert "require token presence for live mode" in text
    assert "22D.5 -- Real Lichess Level 2 SQI Autoplay Run and Result Receipt" in text
    assert "Lock ID: AION-PHASE22D4-FULL-CHESS-LIVE-LICHESS-AUTOPLAY-V2-SQI-LEVEL2-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
