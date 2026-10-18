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


def test_phase22c2_composer_matches_css_contract():
    block = function_block("renderAionPilotSimpleTaskStream")
    assert 'class="aion-pilot-composer-bar"' in block
    assert 'class="aion-pilot-composer-row"' not in block
    assert '<label for="aion-pilot-mission-input">Ask Pilot</label>' not in block


def test_phase22c2_button_is_action_language():
    block = function_block("renderAionPilotSimpleTaskStream")
    assert "getAionPilotCommandButtonLabel(pilotState, hasDraft)" in block
    assert "getAionPilotCommandButtonLabel(pilotState, hasDraft)" in block
    assert "Create plan" not in block


def test_phase22c2_button_keeps_existing_click_hook():
    block = function_block("renderAionPilotSimpleTaskStream")
    assert "data-aion-pilot-create-draft-mission" in block
    assert "createAionPilotFrontendDraftMission" in TEXT


def test_phase22c2_start_task_label_still_exists_in_command_helper():
    assert "Start task" in TEXT

def test_phase22c2_command_button_helper_controls_thread_labels():
    assert "function getAionPilotCommandButtonLabel" in TEXT
    assert "Start task" in TEXT
    assert "Send to Pilot" in TEXT
    assert "Send revision" in TEXT
