from pathlib import Path


def test_phase21l_strategy_learning_kernel_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21l_strategy_learning_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21L: Strategy Learning Kernel Lock" in text
    assert "explore\\_unknown" in text
    assert "repeat\\_last\\_success" in text
    assert "avoid\\_last\\_failure" in text
    assert "strategy \\rightarrow action \\rightarrow reward" in text
    assert "final\\_strategy\\_trust" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21L-STRATEGY-LEARNING-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
