from pathlib import Path


def test_phase22d7_level2_sqi_loss_review_doc_lock_exists():
    path = Path("docs/rfc/aion_phase22d7_full_chess_level2_sqi_loss_post_game_review_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 22D.7: Level 2 SQI Loss Post-Game Review Kernel Lock" in text
    assert "level 2 SQI loss reviewed and policy updates generated" in text
    assert "lynbgdRG" in text
    assert "repetition loops" in text
    assert "queen and rook invasion" in text
    assert "promotion race" in text
    assert "22D.8 -- Patch SQI Selector Against Level 2 Failure Modes" in text
    assert "Lock ID: AION-PHASE22D7-LEVEL2-SQI-LOSS-POST-GAME-REVIEW-KERNEL-LOCK" in text
