from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _function_block(name: str) -> str:
    text = APP_JS.read_text()
    marker = f"function {name}"
    start = text.find(marker)
    assert start != -1, f"Missing function {name}"

    brace_start = text.find("{", start)
    assert brace_start != -1

    depth = 0
    in_single = False
    in_double = False
    in_template = False
    escaped = False

    for index in range(brace_start, len(text)):
        char = text[index]

        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if in_single:
            if char == "'":
                in_single = False
            continue

        if in_double:
            if char == '"':
                in_double = False
            continue

        if in_template:
            if char == "`":
                in_template = False
            continue

        if char == "'":
            in_single = True
        elif char == '"':
            in_double = True
        elif char == "`":
            in_template = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    raise AssertionError(f"Could not extract function {name}")


def test_phase22h_priority_step_output_is_not_home_fixed_hardcoded():
    block = _function_block("buildAionPilotPriorityStepOutput")

    forbidden = [
        "Sales Launch Pack",
        "Draft Marketing Asset Set",
        "Lead Capture Workflow",
        "Landing Page Outline",
        "Roof leak or home repair needed?",
        "Home Fixed roof repair and home maintenance enquiry",
        "Reliable home repairs and roof leak support from Home Fixed",
    ]

    for marker in forbidden:
        assert marker not in block


def test_phase22h_priority_step_output_uses_plan_steps():
    block = _function_block("buildAionPilotPriorityStepOutput")

    assert "safePlan.safe_steps" in block
    assert "safePlan.steps" in block
    assert "safePlan.draft_steps" in block
    assert "safePlan.deliverables" in block
    assert "safePlan.expected_outputs" in block
    assert "normalisedSteps" in block
    assert "selectedStep" in block
    assert "Still approval-gated:" in block
    assert "Draft/preview work only. No live external action has been taken." in block


def test_phase22h_no_bottom_override_was_added():
    text = APP_JS.read_text()
    assert text.count("function buildAionPilotPriorityStepOutput") == 1

def test_phase22h_next_step_titles_are_derived_from_output_text():
    text = APP_JS.read_text()
    assert "function getAionPilotStepOutputTitle" in text
    assert "const stepOutputTitle = getAionPilotStepOutputTitle" in text
    assert "title: stepOutputTitle" in text
    assert "output_label: stepOutputTitle" in text
    assert "pilotState.output_panel_title = stepOutputTitle" in text


def test_phase22h_step_selection_accounts_for_step_one_business_plan_output():
    block = _function_block("buildAionPilotPriorityStepOutput")
    assert "const selectedStepIndex = Math.max(0, stepNumber - 2);" in block
    assert "normalisedSteps[selectedStepIndex]" in block
    assert "safePlan.draftSteps" in block
    assert "safePlan.work_package?.draft_steps" in block
