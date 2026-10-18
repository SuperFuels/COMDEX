from pathlib import Path


def test_phase22e29_lock_doc_exists_and_names_opponent_threat_map():
    path = Path("docs/rfc/aion_phase22e29_full_chess_opponent_threat_map_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.29" in text
    assert "Opponent Threat Map" in text
    assert "recommended_response_mode" in text
    assert "critical threat" in text
    assert "Stockfish" in text
    assert "LLM" in text
