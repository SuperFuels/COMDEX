from pathlib import Path


def test_phase22c3_depth_limited_search_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22c3_full_chess_depth_limited_lookahead_search_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22C.3: Full Chess Depth-Limited Lookahead Search Kernel Lock" in text
    assert "depth-limited lookahead search implemented and tested" in text
    assert "full_chess_depth_limited_lookahead_search_kernel.py" in text
    assert "simulate future legal continuations up to a depth limit" in text
    assert "include opponent replies" in text
    assert "evaluate leaf positions with the Phase 22C.1 evaluator" in text
    assert "prioritise terminal mate moves" in text
    assert "22C.4 -- Live Lichess Loop Uses Evaluator/Search Selector" in text
    assert "Lock ID: AION-PHASE22C3-FULL-CHESS-DEPTH-LIMITED-LOOKAHEAD-SEARCH-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
