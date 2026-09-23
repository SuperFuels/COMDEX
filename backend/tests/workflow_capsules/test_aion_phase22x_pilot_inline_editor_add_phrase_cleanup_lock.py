from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def _function_block(name: str) -> str:
    marker = f"function {name}"
    start = TEXT.find(marker)
    assert start != -1

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

    raise AssertionError("Could not extract function")


def test_phase22x_add_phrase_cleanup_exists():
    block = _function_block("applyAionPilotSimpleMissionThreadRevision")
    assert "cleanAionPilotAddedPhrase" in block
    assert "to|into|onto" in block
    assert "plan|list|section|draft|document" in block


def test_phase22x_add_operation_still_tracks_added_line():
    block = _function_block("applyAionPilotSimpleMissionThreadRevision")
    assert "Added:" in block
    assert "addOperations" in block
    assert "normaliseAddedLine" in block


def test_phase22x_twitter_posts_route_to_content_plan():
    block = _function_block("applyAionPilotSimpleMissionThreadRevision")
    assert "twitter" in block
    assert "content plan" in block
    assert "marketing channels" in block
