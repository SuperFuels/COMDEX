from pathlib import Path


def test_phase22e35_lock_doc_exists_and_names_live_sender_integration():
    path = Path("docs/rfc/aion_phase22e35_full_chess_level2_strategic_well_live_sender_integration_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.35" in text
    assert "Strategic Regression Well" in text
    assert "live Level-2 sender" in text
    assert "sender-ready envelope" in text
    assert "safe_to_send" in text
    assert "does not POST" in text
    assert "Stockfish" in text
    assert "LLM" in text
