from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def _function_block(name: str) -> str:
    marker = f"function {name}"
    start = TEXT.find(marker)
    assert start != -1, f"Missing function {name}"

    signature_end = TEXT.find(") {", start)
    assert signature_end != -1
    brace_start = signature_end + 2

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


def test_phase22w_no_duplicate_override_block_left():
    assert "PHASE 22W LOCK: in-place tracked mission draft override" not in TEXT


def test_phase22w_functions_are_single_definition():
    for name in [
        "getAionPilotLatestEditableOutputText",
        "applyAionPilotSimpleMissionThreadRevision",
        "applyAionPilotCommandBarRevisionIfActive",
        "appendAionPilotStepOutput",
        "renderAionPilotStepOutputCards",
    ]:
        assert TEXT.count(f"function {name}") == 1


def test_phase22w_mission_thread_edits_latest_output_in_place():
    block = _function_block("applyAionPilotCommandBarRevisionIfActive")
    assert 'commandMode === "mission_thread"' in block
    assert "getAionPilotLatestEditableOutput(pilotState)" in block
    assert "revised_in_place: true" in block
    assert "Edited current working draft in place" in block


def test_phase22w_revision_does_not_create_mission_revision_output_for_thread_mode():
    block = _function_block("applyAionPilotCommandBarRevisionIfActive")
    thread_part = block.split('if (commandMode === "mission_thread")', 1)[1].split('const stepNumber = Number(pilotState.current_step_index', 1)[0]
    assert "Mission revision:" not in thread_part
    assert "buildAionPilotMissionThreadRevisionOutput" not in thread_part


def test_phase22w_revision_engine_removes_and_adds_matching_lines():
    block = _function_block("applyAionPilotSimpleMissionThreadRevision")
    assert "normaliseLineForEditMatch" in block
    assert "request.includes(comparable)" in block
    assert "Removed:" in block
    assert "Added:" in block
    assert "addOperations" in block


def test_phase22w_step_output_preserves_tracked_change_metadata():
    block = _function_block("appendAionPilotStepOutput")
    assert "change_log" in block
    assert "revision_instruction" in block
    assert "revised_in_place" in block


def test_phase22w_renderer_shows_tracked_change_strip():
    block = _function_block("renderAionPilotStepOutputCards")
    assert "aion-pilot-output-revised" in block
    assert "Edited in place" in block
    assert "Tracked changes" in block
    assert "aion-pilot-tracked-change-strip" in block


def test_phase22w_tracked_edit_css_exists():
    assert "PHASE 22W LOCK: tracked in-place mission draft edits" in TEXT
    assert "aion-pilot-tracked-change-badge" in TEXT
    assert "#6f42c1" in TEXT
