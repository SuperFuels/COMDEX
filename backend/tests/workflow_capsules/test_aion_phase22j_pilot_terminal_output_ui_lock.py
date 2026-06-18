from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def _function_block(name: str) -> str:
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


def test_phase22j_outputs_print_directly_without_intermediate_output_card():
    block = _function_block("renderAionPilotStepOutputCards")

    assert "aion-pilot-terminal-output" in block
    assert "normaliseAionPilotPreviewText(item.output_text || \"\")" in block
    assert "Open output" not in block
    assert "Download output" not in block
    assert "View receipt" not in block
    assert "Draft completed. Review it, download it, or inspect the receipt." not in block


def test_phase22j_priority_output_uses_real_newlines_not_literal_backslash_n():
    block = _function_block("buildAionPilotPriorityStepOutput")

    assert '].join("\\n");' in block
    assert '].join("\\\\n");' not in block


def test_phase22j_terminal_output_has_no_inner_scroll_panel_class():
    assert "aion-pilot-terminal-output" in TEXT
    assert "installAionPilotTerminalOutputStylesPhase22J" in TEXT
    assert "max-height: none !important" in TEXT
    assert "overflow: visible !important" in TEXT


def test_phase22j_actions_are_terminal_links():
    assert "aion-pilot-terminal-output-style-phase22j" in TEXT
    assert "text-decoration: underline !important" in TEXT
    assert "border: 0 !important" in TEXT


def test_phase22j_core_actions_still_exist():
    for marker in [
        "data-aion-pilot-download-output",
        "data-aion-pilot-view-receipt",
        "data-aion-pilot-feedback-approve",
        "data-aion-pilot-feedback-revise",
        "data-aion-pilot-feedback-stop",
    ]:
        assert marker in TEXT
