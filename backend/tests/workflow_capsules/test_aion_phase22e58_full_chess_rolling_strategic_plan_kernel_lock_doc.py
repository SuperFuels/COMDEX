from pathlib import Path


def test_phase22e58_doc_lock_exists_and_names_kernel():
    doc = Path("docs/rfc/aion_phase22e58_full_chess_rolling_strategic_plan_kernel_lock.tex")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")

    assert "Phase 22E.58" in text
    assert "Rolling Strategic Plan Kernel" in text
    assert "primary plan" in text
    assert "fallback plan" in text
    assert "Lock ID: AION-PHASE22E58-FULL-CHESS-ROLLING-STRATEGIC-PLAN" in text
