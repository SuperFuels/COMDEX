from pathlib import Path


def test_phase21s_multi_world_survival_curriculum_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21s_multi_world_survival_curriculum_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21S: Multi-World Survival Curriculum Kernel Lock" in text
    assert "world_1 \\rightarrow survival\\_memory" in text
    assert "curriculum\\_policy" in text
    assert "worlds\\_run" in text
    assert "worlds\\_survived" in text
    assert "curriculum\\_score" in text
    assert "uses\\_multi\\_world\\_curriculum" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21S-MULTI-WORLD-SURVIVAL-CURRICULUM-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
