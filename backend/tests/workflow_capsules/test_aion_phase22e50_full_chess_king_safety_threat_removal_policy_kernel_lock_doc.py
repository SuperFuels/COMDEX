from pathlib import Path


def test_phase22e50_lock_doc_exists_and_names_king_safety_threat_removal():
    path = Path("docs/rfc/aion_phase22e50_full_chess_king_safety_threat_removal_policy_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.50" in text
    assert "King Safety" in text
    assert "Threat-Removal" in text
    assert "passive king-walking" in text
    assert "Stockfish" in text
    assert "LLM" in text
