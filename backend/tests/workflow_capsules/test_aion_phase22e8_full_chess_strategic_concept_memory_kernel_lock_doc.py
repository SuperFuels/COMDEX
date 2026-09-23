from pathlib import Path


def test_phase22e8_lock_doc_exists_and_names_strategic_concept_memory():
    path = Path("docs/rfc/aion_phase22e8_full_chess_strategic_concept_memory_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.8" in text
    assert "Strategic Concept Memory" in text
    assert "king safety recovery" in text
    assert "promotion defence protocol" in text
    assert "Stockfish" in text
    assert "LLM" in text
