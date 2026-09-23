from pathlib import Path


def test_phase22e27_lock_doc_exists_and_names_zugzwang():
    path = Path("docs/rfc/aion_phase22e27_full_chess_zugzwang_choice_architecture_selector_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.27" in text
    assert "Zugzwang Choice Architecture Selector" in text
    assert "opponent reply set" in text
    assert "choice width" in text
    assert "Stockfish" in text
    assert "LLM" in text
