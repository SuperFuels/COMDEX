from pathlib import Path


def test_phase22e12_lock_doc_exists_and_names_live_dry_run_adapter():
    path = Path("docs/rfc/aion_phase22e12_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.12" in text
    assert "Concept-Guided Live Lichess Dry-Run Adapter" in text
    assert "dry-run only" in text
    assert "no move POST" in text
    assert "no live Lichess" in text
    assert "Stockfish" in text
    assert "LLM" in text
