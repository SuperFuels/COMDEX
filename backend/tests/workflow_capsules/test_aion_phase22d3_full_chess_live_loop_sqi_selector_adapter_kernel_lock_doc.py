from pathlib import Path


def test_phase22d3_live_loop_sqi_selector_adapter_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22d3_full_chess_live_loop_sqi_selector_adapter_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22D.3: Full Chess Live Loop SQI Selector Adapter Kernel Lock" in text
    assert "live loop SQI selector adapter implemented and tested" in text
    assert "full_chess_live_loop_sqi_selector_adapter_kernel.py" in text
    assert "call the Phase 22D.2 SQI-guided selector" in text
    assert "preserve SQI trace and selection trace hashes" in text
    assert "avoid sending live Lichess moves in this phase" in text
    assert "22D.4 -- Live Lichess Autoplay v2 Uses SQI-Guided Selector" in text
    assert "Lock ID: AION-PHASE22D3-FULL-CHESS-LIVE-LOOP-SQI-SELECTOR-ADAPTER-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
