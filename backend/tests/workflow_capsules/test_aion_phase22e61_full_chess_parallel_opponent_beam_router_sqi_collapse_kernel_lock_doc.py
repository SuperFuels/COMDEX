from pathlib import Path


def test_phase22e61_doc_lock_exists_and_names_parallel_router():
    doc = Path("docs/rfc/aion_phase22e61_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel_lock.tex")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")

    assert "Phase 22E.61" in text
    assert "Parallel Opponent Beam Router" in text
    assert "SQI Collapse" in text
    assert "1000" in text
    assert "HexCore" in text
    assert "QQC" in text
    assert "Lock ID: AION-PHASE22E61-FULL-CHESS-PARALLEL-OPPONENT-BEAM-ROUTER-SQI-COLLAPSE" in text
