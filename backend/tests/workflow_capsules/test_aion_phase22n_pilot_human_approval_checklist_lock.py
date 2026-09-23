from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22n_human_approval_helpers_exist():
    for marker in [
        "function getAionPilotHumanApprovalStages",
        "function getAionPilotHumanApprovalStageKey",
        "function toggleAionPilotHumanApprovalStage",
        "function renderAionPilotHumanApprovalChecklist",
        "window.toggleAionPilotHumanApprovalStage",
    ]:
        assert marker in TEXT


def test_phase22n_work_package_uses_task_approval_checklist():
    start = TEXT.index("function renderAionPilotWorkPackageCard")
    end = TEXT.index("function normaliseAionPilotPreviewText", start)
    block = TEXT[start:end]

    assert "renderAionPilotHumanApprovalChecklist(workPackage, state)" in block
    assert "<ul>${steps}</ul>" not in block
    assert "Safety boundary" not in block
    assert "workPackage.output_assets" not in block
    assert "data-aion-pilot-output-assets" not in block


def test_phase22n_approval_checklist_copy_and_toggle_are_visible():
    block_start = TEXT.index("function renderAionPilotHumanApprovalChecklist")
    block_end = TEXT.index("window.toggleAionPilotHumanApprovalStage", block_start)
    block = TEXT[block_start:block_end]

    assert "Tick only the stages that must pause for human approval" in block
    assert "Unticked stages can run as safe draft work" in block
    assert "data-aion-pilot-approval-stage-toggle" in block
    assert "✓ Approval" in block
    assert "Approval" in block


def test_phase22n_click_handler_installed():
    assert "__aionPilotHumanApprovalStageClickHandlerInstalled" in TEXT
    assert 'closest?.("[data-aion-pilot-approval-stage-toggle]")' in TEXT
    assert "toggleAionPilotHumanApprovalStage(button.getAttribute" in TEXT


def test_phase22n_css_installed():
    assert "PHASE 22N LOCK: Pilot human approval checklist" in TEXT
    assert "aion-pilot-approval-stage-row" in TEXT
    assert "aion-pilot-approval-stage-toggle.is-selected" in TEXT
