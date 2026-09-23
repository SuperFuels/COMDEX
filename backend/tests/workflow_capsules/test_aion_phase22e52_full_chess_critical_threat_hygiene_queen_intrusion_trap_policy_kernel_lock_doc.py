from pathlib import Path


def test_phase22e52_lock_doc_exists_and_names_critical_threat_hygiene():
    path = Path("docs/rfc/aion_phase22e52_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel_lock.tex")
    assert path.exists()

    text = path.read_text(encoding="utf-8")
    assert "Phase 22E.52" in text
    assert "Critical Threat Hygiene" in text
    assert "Queen Intrusion" in text
    assert "h2h4" in text
    assert "Stockfish" in text
    assert "LLM" in text
