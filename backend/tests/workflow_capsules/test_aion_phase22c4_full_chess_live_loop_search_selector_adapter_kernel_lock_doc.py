from pathlib import Path


def test_phase22c4_live_loop_search_selector_adapter_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22c4_full_chess_live_loop_search_selector_adapter_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22C.4: Full Chess Live Loop Search Selector Adapter Kernel Lock" in text
    assert "live loop search selector adapter implemented and tested" in text
    assert "full_chess_live_loop_search_selector_adapter_kernel.py" in text
    assert "determine whether it is AION's turn" in text
    assert "call the Phase 22C.3 depth-limited search selector" in text
    assert "emit no move when it is not AION's turn" in text
    assert "replace the old heuristic picker" in text
    assert "does not send a live Lichess move" in text
    assert "22C.5 -- Live Lichess Autoplay v2 Against Stockfish Level 2" in text
    assert "Lock ID: AION-PHASE22C4-FULL-CHESS-LIVE-LOOP-SEARCH-SELECTOR-ADAPTER-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
