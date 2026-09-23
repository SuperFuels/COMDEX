from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _function_block(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0

    for idx in range(brace, len(text)):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]

    raise AssertionError(f"Could not find end of function: {signature}")


def test_phase23j_apply_payload_preserves_loop_index_for_same_mission():
    text = APP.read_text()

    assert "previousMissionSignature" in text
    assert "nextMissionSignature" in text
    assert "shouldPreserveLoopIndex" in text
    assert "mission_loop_signature" in text
    assert "pilotState.mission_loop_index = shouldPreserveLoopIndex" in text


def test_phase23j_runner_continues_existing_queue_before_fetching_again():
    text = APP.read_text()
    block = _function_block(text, "async function runAionPilotSafeWorkPreview")

    assert "existingMissionQueue" in block
    assert "existingMissionIndex" in block
    assert 'backend_mission_preview_status === "loaded"' in block
    assert "Continuing existing backend mission queue" in block
    assert "await executeAndAppendAionPilotMissionMapStepOutput" in block

    existing_queue_pos = block.index("Continuing existing backend mission queue")
    fetch_pos = block.index("Fetching backend mission preview")
    assert existing_queue_pos < fetch_pos


def test_phase23j_fetch_stores_raw_backend_preview_for_queue_continuation():
    text = APP.read_text()

    assert "state.backend_mission_preview = previewPayload" in text
