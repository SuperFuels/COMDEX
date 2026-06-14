from pathlib import Path


def test_phase22e54_documentation_lock_exists_and_names_boundaries():
    doc = Path("docs/rfc/aion_phase22e54_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel_lock.tex")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")

    assert "Phase 22E.54" in text
    assert "Opponent Reply Probability" in text
    assert "Tactical Exposure Guard" in text
    assert "does not call Stockfish" in text
    assert "does not use LLM move judgement" in text
    assert "does not use Lichess analysis" in text
    assert "Lock ID: AION-PHASE22E54-OPPONENT-REPLY-PROBABILITY-TACTICAL-EXPOSURE-GUARD" in text
