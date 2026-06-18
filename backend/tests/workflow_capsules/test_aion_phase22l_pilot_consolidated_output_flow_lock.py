from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22l_no_separate_contract_card():
    assert "data-aion-pilot-contract-card" not in TEXT
    assert "Approve plan to run safe work" not in TEXT
    assert "This will generate the draft output only" not in TEXT


def test_phase22l_approval_actions_live_inside_work_package():
    start = TEXT.index("function renderAionPilotWorkPackageCard")
    end = TEXT.index("function normaliseAionPilotPreviewText", start)
    block = TEXT[start:end]

    assert "data-aion-pilot-work-package-actions" in block
    assert 'data-aion-pilot-feedback-approve' in block
    assert ">Approve<" in block or '"Approve"' in block
    assert ">Revise<" in block
    assert ">Stop<" in block


def test_phase22l_safe_work_completed_goes_straight_to_output():
    start = TEXT.index("function renderAionPilotSimpleTaskStream")
    end = TEXT.index("function renderAionPilotAdvancedTechnicalDetails", start)
    block = TEXT[start:end]

    assert "renderAionPilotStepOutputCards(pilotState)" in block
    assert "renderAionPilotStepCheckpointCard(pilotState)" not in block
    assert "data-aion-pilot-contract-card" not in block


def test_phase22l_outputs_print_directly_no_intermediate_open_card():
    start = TEXT.index("function renderAionPilotStepOutputCards")
    end = TEXT.index("function openAionPilotStepOutput", start)
    block = TEXT[start:end]

    assert "aion-pilot-terminal-output" in block
    assert "Open output" not in block
    assert "Download output" not in block
    assert "View receipt" not in block
    assert "Draft completed. Review it, download it, or inspect the receipt." not in block
