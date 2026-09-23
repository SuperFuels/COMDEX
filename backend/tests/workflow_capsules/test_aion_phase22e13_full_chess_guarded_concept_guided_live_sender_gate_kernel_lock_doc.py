from pathlib import Path


def test_phase22e13_lock_doc_exists_and_names_guarded_gate():
    path = Path("docs/rfc/aion_phase22e13_full_chess_guarded_concept_guided_live_sender_gate_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.13" in text
    assert "Guarded Concept-Guided Live Sender Gate" in text
    assert "send blocked" in text
    assert "no move POST" in text
    assert "no live Lichess" in text
    assert "Stockfish" in text
    assert "LLM" in text
