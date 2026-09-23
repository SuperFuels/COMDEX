from pathlib import Path


def test_phase22e60_doc_lock_exists_and_names_connected_stack():
    doc = Path("docs/rfc/aion_phase22e60_full_chess_opponent_response_beam_planner_kernel_lock.tex")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")

    assert "Phase 22E.60" in text
    assert "Opponent Response Beam Planner" in text
    assert "SQIBeamKernel" in text
    assert "HexCore" in text
    assert "QQC" in text
    assert "container evidence" in text
    assert "Lock ID: AION-PHASE22E60-FULL-CHESS-OPPONENT-RESPONSE-BEAM-PLANNER" in text
