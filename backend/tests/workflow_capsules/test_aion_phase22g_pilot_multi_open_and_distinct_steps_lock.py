from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = TEXT.index(f"function {name}")
    brace = TEXT.index("{", TEXT.index(")", start))
    depth = 0
    in_string = None
    escape = False

    for i in range(brace, len(TEXT)):
        ch = TEXT[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            continue

        if ch in ("'", '"', "`"):
            in_string = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return TEXT[start:i + 1]

    raise AssertionError(f"function not closed: {name}")


def test_phase22g_outputs_have_independent_open_state():
    block = function_block("renderAionPilotStepOutputCards")
    assert "const isOpen = item.open === true" in block
    assert "data-aion-pilot-inline-output-panel" in block
    assert "data-aion-pilot-close-step-output" in block


def test_phase22g_open_step_does_not_close_other_steps():
    block = function_block("openAionPilotStepOutput")
    assert "open: true" in block
    assert "open: false" not in block


def test_phase22g_close_step_only_closes_selected_step():
    block = function_block("closeAionPilotStepOutput")
    assert "open: false" in block
    assert "Number(item.step_number) !== selectedNumber" in block


def test_phase22g_priority_builder_has_distinct_business_steps():
    block = function_block("buildAionPilotPriorityStepOutput")
    assert "stepNumber === 2" in block
    assert "Sales Launch Pack" in block
    assert "stepNumber === 3" in block
    assert "Draft Marketing Asset Set" in block
    assert "stepNumber === 4" in block
    assert "Lead Capture Workflow" in block
    assert "stepNumber === 5" in block
    assert "Landing Page Outline" in block


def test_phase22g_append_output_defaults_open():
    block = function_block("appendAionPilotStepOutput")
    assert "open: step.open !== false" in TEXT


def test_phase22g_close_handler_is_wired():
    assert "data-aion-pilot-close-step-output" in TEXT
    assert "closeAionPilotStepOutput" in TEXT
