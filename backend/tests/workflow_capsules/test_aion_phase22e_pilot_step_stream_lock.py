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


def test_phase22e_step_stream_helpers_exist():
    assert "function appendAionPilotStepOutput" in TEXT
    assert "function renderAionPilotStepOutputCards" in TEXT
    assert "function openAionPilotStepOutput" in TEXT


def test_phase22e_step1_is_appended_not_single_slot_only():
    block = function_block("runAionPilotSafeWorkPreview")
    assert "appendAionPilotStepOutput" in block
    assert "step_number: 1" in block
    assert "frontend_step1_artifact" in block


def test_phase22e_run_next_safe_step_appends_next_step():
    block = function_block("approveAionPilotMissionContract")
    assert "nextStepNumber" in block
    assert "appendAionPilotStepOutput" in block
    assert "buildAionPilotPriorityStepOutput" in block
    assert "priority_step_runner" in block


def test_phase22e_output_panel_uses_selected_body_not_recomputed_plan():
    block = function_block("renderAionPilotOutputPanel")
    assert "const body = pilotState.output_panel_body ||" in block
    assert "getAionPilotOutputPreviewText(plan, pilotState)" not in block


def test_phase22e_stream_renders_step_output_cards():
    block = function_block("renderAionPilotSimpleTaskStream")
    assert "renderAionPilotStepOutputCards(pilotState)" in block
    assert "data-aion-pilot-results-card" not in block


def test_phase22e_click_handler_opens_selected_step_output():
    assert "data-aion-pilot-open-step-output" in TEXT
    assert "openAionPilotStepOutput" in TEXT
