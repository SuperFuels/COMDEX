from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22a_business_plan_classifier_exists():
    assert 'task_type: "business_plan"' in TEXT
    assert "Create business plan" in TEXT
    assert "Business plan draft" in TEXT


def test_phase22a_business_plan_work_package_exists():
    for token in [
        "Business plan package",
        "Target customer profile",
        "Pricing and callout model",
        "Marketing plan",
        "Operations workflow",
        "90-day action plan",
    ]:
        assert token in TEXT


def test_phase22a_business_plan_output_is_real_not_generic():
    for token in [
        "Business Plan Draft:",
        "Business Overview",
        "Main Services",
        "Pricing Model",
        "Operations Workflow",
        "90-Day Action Plan",
    ]:
        assert token in TEXT


def test_phase22a_new_plan_resets_approval_state():
    for token in [
        'pilotState.contract_status = "draft_contract";',
        'pilotState.safe_work_status = "waiting_approval";',
        "pilotState.generated_output_text = \"\";",
        "pilotState.output_panel_open = false;",
    ]:
        assert token in TEXT


def test_phase22a_lrm_replaced_with_reasoning_mini_status():
    assert "function renderAionPilotReasoningMiniStatus" in TEXT
    assert "data-aion-phase22a-reasoning-mini-status" in TEXT
    assert "${renderAionPilotReasoningMiniStatus(pilotState)}" in TEXT
