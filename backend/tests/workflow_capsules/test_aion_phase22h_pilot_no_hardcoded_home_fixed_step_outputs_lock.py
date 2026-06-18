from pathlib import Path




APP_JS = Path("desktop/mac/src/app.js")
TEXT = APP_JS.read_text(encoding="utf-8")


def function_block(name: str) -> str:
    marker = f"function {name}"
    start = TEXT.find(marker)
    assert start != -1, f"Missing function {name}"

    brace_start = TEXT.find("{", start)
    assert brace_start != -1

    depth = 0
    in_single = False
    in_double = False
    in_template = False
    escaped = False

    for index in range(brace_start, len(TEXT)):
        char = TEXT[index]

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
                return TEXT[start:index + 1]

    raise AssertionError(f"Could not extract function {name}")


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



def test_phase22h_priority_step_output_uses_queue_runner():
    block = function_block("buildAionPilotPriorityStepOutput")
    assert "getAionPilotNextExecutableFollowOnWorkItem" in block
    assert "buildAionPilotFollowOnTaskDraftOutput" in block
    assert "completed[nextFollowOn.key] = true" in block
    assert "Prepare the next safe draft output" not in block

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


def test_phase22h_step_selection_accounts_for_follow_on_queue_completion():
    block = function_block("buildAionPilotPriorityStepOutput")
    assert "nextFollowOn.blocked_for_approval === true" in block
    assert "Approval required" in block
    assert "No further safe draft work available" in block

