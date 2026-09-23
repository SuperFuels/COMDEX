from pathlib import Path


def test_phase21t_curriculum_difficulty_escalation_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21t_curriculum_difficulty_escalation_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21T: Curriculum Difficulty Escalation Kernel Lock" in text
    assert "easy\\_world \\rightarrow harder\\_worlds" in text
    assert "score\\_pressure" in text
    assert "difficulty\\_score\\_delta" in text
    assert "difficulty\\_improved" in text
    assert "uses\\_curriculum\\_difficulty\\_escalation" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21T-CURRICULUM-DIFFICULTY-ESCALATION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
