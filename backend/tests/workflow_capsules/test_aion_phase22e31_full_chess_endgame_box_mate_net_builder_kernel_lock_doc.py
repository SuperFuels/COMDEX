from pathlib import Path


def test_phase22e31_lock_doc_exists_and_names_mate_net_builder():
    path = Path("docs/rfc/aion_phase22e31_full_chess_endgame_box_mate_net_builder_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.31" in text
    assert "Endgame Box/Mate Net Builder" in text
    assert "enemy king mobility" in text
    assert "mate-net" in text
    assert "Stockfish" in text
    assert "LLM" in text
