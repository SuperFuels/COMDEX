from pathlib import Path


def test_phase22d5_real_level2_sqi_runner_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22d5_real_lichess_level2_sqi_autoplay_runner_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22D.5: Real Lichess Level 2 SQI Autoplay Runner Kernel Lock" in text
    assert "real level 2 SQI autoplay runner implemented and tested in dry-run mode" in text
    assert "full_chess_real_lichess_level2_sqi_autoplay_runner_kernel.py" in text
    assert "dry\\_run = false" in text
    assert "network\\_enabled = true" in text
    assert "LICHESS\\_BOT\\_TOKEN" in text
    assert "AION\\_LICHESS\\_LIVE=1" in text
    assert "Phase 22D.3 live-loop SQI adapter" in text
    assert "Phase 22D.2 SQI-guided move selector" in text
    assert "Lock ID: AION-PHASE22D5-REAL-LICHESS-LEVEL2-SQI-AUTOPLAY-RUNNER-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
