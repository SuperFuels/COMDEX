from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
TEXT = TEXT


def test_phase22v_revision_append_uses_single_step_object():
    assert "appendAionPilotStepOutput({" in TEXT
    assert "appendAionPilotStepOutput(pilotState," not in TEXT


def test_phase22v_revision_output_fields_match_renderer():
    assert "step_number: stepNumber" in TEXT
    assert "title," in TEXT or "title:" in TEXT
    assert "output_text: revision.revised_text" in TEXT
    assert "open: true" in TEXT


def test_phase22v_revision_stays_inside_mission_thread():
    assert "applyAionPilotSimpleMissionThreadRevision" in TEXT
    assert "Edited current working draft in place" in TEXT
    assert "pilotState.last_request = commandText" not in TEXT
