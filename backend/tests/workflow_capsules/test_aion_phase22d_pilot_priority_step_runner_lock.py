from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = TEXT.index(f"function {name}")
    brace = TEXT.index("{", start)
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


def test_phase22d_priority_step_builder_exists():
    block = function_block("buildAionPilotPriorityStepOutput")
    assert "Step 2: Sales Launch Pack" in block
    assert "Priority Order" in block
    assert "Lead Capture Workflow" in block
    assert "Draft Advert" in block
    assert "Blocked Until Exact Approval" in block


def test_phase22d_run_next_safe_step_generates_step2_output():
    block = function_block("approveAionPilotMissionContract")
    assert "buildAionPilotPriorityStepOutput(plan, pilotState)" in block
    assert 'pilotState.output_panel_title = "Step 2 output";' in block
    assert "priority_step_runner" in block
    assert "Step 2 safe work completed" in block


def test_phase22d_typo_business_plan_classifier_present():
    assert "busines plan" in TEXT
    assert "business_plan" in TEXT
