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


def test_phase22f_selected_step_number_is_stored():
    block = function_block("openAionPilotStepOutput")
    assert "open: true" in block
    assert "output_panel_step_number" not in block


def test_phase22f_step_panel_renders_inline_under_selected_card():
    block = function_block("renderAionPilotStepOutputCards")
    assert "const isOpen = item.open === true" in block
    assert "data-aion-pilot-inline-output-panel" in block
    assert "renderAionPilotOutputPanel()" not in block


def test_phase22f_checkpoint_card_exists_after_step_outputs():
    assert "function renderAionPilotStepCheckpointCard" in TEXT
    block = function_block("renderAionPilotSimpleTaskStream")
    assert "renderAionPilotStepOutputCards(pilotState)" in block
    assert "renderAionPilotStepCheckpointCard(pilotState)" in block


def test_phase22f_checkpoint_has_run_next_safe_step_button():
    block = function_block("renderAionPilotStepCheckpointCard")
    assert "Run next safe step" in block
    assert "data-aion-pilot-feedback-approve" in block
    assert "Ready for Step" in block


def test_phase22f_generated_step_selects_itself():
    block = function_block("approveAionPilotMissionContract")
    assert "output_panel_step_number = nextStepNumber" in block
    assert "output_panel_kind = \"step_output\"" in block
