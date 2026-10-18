from pathlib import Path


def test_phase21o_active_exploration_rule_repair_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21o_active_exploration_rule_repair_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21O: Active Exploration and Rule Repair Kernel Lock" in text
    assert "failed\\_generalisation \\rightarrow active\\_exploration" in text
    assert "prediction\\_repair" in text
    assert "rule\\_repair" in text
    assert "score\\_after\\_repair" in text
    assert "uses\\_active\\_exploration" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21O-ACTIVE-EXPLORATION-RULE-REPAIR-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
