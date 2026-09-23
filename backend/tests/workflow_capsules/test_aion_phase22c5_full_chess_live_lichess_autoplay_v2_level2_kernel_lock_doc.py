from pathlib import Path


def test_phase22c5_live_lichess_autoplay_v2_level2_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22c5_full_chess_live_lichess_autoplay_v2_level2_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22C.5: Full Chess Live Lichess Autoplay v2 Level 2 Kernel Lock" in text
    assert "guarded autoplay v2 level 2 path implemented and tested" in text
    assert "opponent_level: 2" in text
    assert "full_chess_live_lichess_autoplay_v2_level2_kernel.py" in text
    assert "target Lichess Stockfish level 2" in text
    assert "Phase 22C.4 live-loop search selector adapter" in text
    assert "Phase 22C.3 depth-limited search selector" in text
    assert "require token presence for live mode" in text
    assert "22C.6 -- Post-Game Review v2 and Policy Update" in text
    assert "Lock ID: AION-PHASE22C5-FULL-CHESS-LIVE-LICHESS-AUTOPLAY-V2-LEVEL2-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
