from pathlib import Path


def test_phase21u_multistep_lookahead_doc_lock_exists():
    path = Path("docs/rfc/aion_phase21u_multistep_lookahead_consequence_simulation_kernel_lock.tex")
    text = path.read_text(encoding="utf-8")

    assert "AION Phase 21U: Multi-Step Lookahead and Consequence Simulation Kernel Lock" in text
    assert "simulate\\_future \\rightarrow predict\\_danger" in text
    assert "future\\_rollouts" in text
    assert "lookahead\\_changed\\_action" in text
    assert "avoided\\_future\\_hazard\\_before\\_impact" in text
    assert "uses\\_multistep\\_lookahead" in text
    assert "uses\\_consequence\\_simulation" in text
    assert "uses\\_llm\\_shortcut = false" in text
    assert "Lock ID: AION-PHASE21U-MULTISTEP-LOOKAHEAD-CONSEQUENCE-SIMULATION-KERNEL-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
