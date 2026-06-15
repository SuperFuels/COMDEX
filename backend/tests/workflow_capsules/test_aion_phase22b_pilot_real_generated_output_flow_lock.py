from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22b_resolved_generated_output_helper_exists():
    assert "function getAionPilotResolvedGeneratedOutput" in TEXT


def test_phase22b_business_plan_forces_real_generated_output():
    assert 'taskType === "business_plan"' in TEXT
    assert "generated_output_text: \"\"" in TEXT
    assert "Business Plan Draft:" in TEXT


def test_phase22b_runner_uses_resolved_output():
    assert "pilotState.generated_output_text = getAionPilotResolvedGeneratedOutput(plan, pilotState);" in TEXT


def test_phase22b_open_and_download_use_resolved_output():
    assert "normaliseAionPilotPreviewText(getAionPilotResolvedGeneratedOutput(plan, pilotState))" in TEXT
    assert "const outputText = normaliseAionPilotPreviewText(getAionPilotResolvedGeneratedOutput(plan, pilotState));" in TEXT


def test_phase22b_create_plan_has_visible_state_change():
    assert 'pilotState.status = "plan_ready";' in TEXT
    assert 'label: "Work package created",' in TEXT
