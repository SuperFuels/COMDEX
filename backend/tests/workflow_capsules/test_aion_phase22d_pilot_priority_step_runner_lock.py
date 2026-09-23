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
    assert "function buildAionPilotPriorityStepOutput" in block
    assert "getAionPilotNextExecutableFollowOnWorkItem" in block
    assert "buildAionPilotFollowOnTaskDraftOutput" in block
    assert "No live external action has been taken" in block

def test_phase22d_run_next_safe_step_generates_step2_output():
    block = function_block("approveAionPilotMissionContract")
    assert "buildAionPilotPriorityStepOutput" in block
    assert "nextStepNumber" in block
    assert "output_panel_title" in block
    assert "priority_step_runner" in block
    assert "safe work completed" in block
    assert "nextStepNumber" in block


def test_phase22d_typo_business_plan_classifier_present():
    assert "busines plan" in TEXT
    assert "business_plan" in TEXT
