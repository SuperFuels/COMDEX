from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22k_pilot_header_copy_is_simple():
    assert "<h2>Pilot</h2>" in TEXT
    assert "It drafts the plan, you choose the human approval stages, and Pilot executes the safe work between them." in TEXT
    assert "Give Pilot a task. It drafts the safe work, then asks before live actions." not in TEXT


def test_phase22k_old_header_layers_hidden():
    assert "PHASE 22K LOCK: simplified Pilot header" in TEXT
    assert "aion-pilot-stream-header::before" in TEXT
    assert "display: none !important" in TEXT
    assert "html body .aion-pilot-status" in TEXT


def test_phase22k_core_pilot_render_survives():
    for marker in [
        "function renderAionPilotSimpleTaskStream",
        "renderAionPilotWorkPackageCard(plan, pilotState)",
        "renderAionPilotStepOutputCards(pilotState)",
        "data-aion-pilot-feedback-approve",
    ]:
        assert marker in TEXT
