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


def test_phase22c4_busines_typo_classifies_as_business_plan():
    assert "busines plan" in TEXT
    assert "business_plan" in TEXT


def test_phase22c4_completed_next_step_runs_priority_step():
    block = function_block("approveAionPilotMissionContract")
    assert 'pilotState.output_panel_kind = "step_output";' in block
    assert "nextStepNumber" in block
    assert "output_panel_title" in block
    assert "buildAionPilotPriorityStepOutput" in block
    assert "priority_step_runner" in block
    assert "safe work completed" in block
    assert "nextStepNumber" in block
