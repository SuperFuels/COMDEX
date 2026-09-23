from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def _function_block(name: str) -> str:
    marker = f"function {name}"
    start = TEXT.find(marker)
    assert start != -1, f"Missing function {name}"

    next_function = TEXT.find("\nfunction ", start + 1)
    if next_function == -1:
        return TEXT[start:]
    return TEXT[start:next_function]


def test_phase22m_work_package_asset_badges_removed():
    block = _function_block("renderAionPilotWorkPackageCard")

    assert "data-aion-pilot-output-assets" not in block
    assert "workPackage.output_assets" not in block
    assert "Business plan draft" not in block
    assert "Action checklist" not in block
    assert "Receipt" not in block


def test_phase22m_approval_trace_states_replace_run_next_button():
    block = _function_block("renderAionPilotWorkPackageCard")

    assert "data-aion-pilot-work-package-actions" in block
    assert "aion-pilot-approval-trace" in block
    assert "✓ Approved" in block
    assert "✓ Revised" in block
    assert "✓ Stopped" in block
    assert "Run next safe output" not in block


def test_phase22m_approval_trace_keeps_actions_available():
    block = _function_block("renderAionPilotWorkPackageCard")

    assert "data-aion-pilot-feedback-approve" in block
    assert "data-aion-pilot-feedback-revise" in block
    assert "data-aion-pilot-feedback-stop" in block


def test_phase22m_approval_trace_css_installed():
    assert "PHASE 22M LOCK: Pilot approval trace" in TEXT
    assert "aion-pilot-trace-approved" in TEXT
    assert "aion-pilot-trace-revised" in TEXT
    assert "aion-pilot-trace-stopped" in TEXT
