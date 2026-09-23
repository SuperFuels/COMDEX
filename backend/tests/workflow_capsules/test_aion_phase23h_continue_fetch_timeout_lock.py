from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_phase23h_mission_preview_fetch_has_timeout_and_abort_controller():
    text = APP.read_text()

    start = text.index("async function fetchAionPilotMissionPreviewIntoPilotState")
    end = text.index("function normaliseAionPilotMissionMapNodeTitle", start)
    block = text[start:end]

    assert "new AbortController()" in block
    assert "setTimeout" in block
    assert "15000" in block
    assert "signal: controller.signal" in block
    assert "clearTimeout(timeoutId)" in block
    assert "timed out after 15 seconds" in block


def test_phase23h_continue_runner_blocks_duplicate_pending_clicks():
    text = APP.read_text()

    start = text.index("async function runAionPilotSafeWorkPreview")
    end = text.index("const plan =", start)
    block = text[start:end]

    assert 'backend_mission_preview_status === "loading"' in block
    assert "ignoring duplicate Continue safe work click" in block
    assert "return;" in block


def test_phase23h_continue_runner_writes_visible_failure_output():
    text = APP.read_text()

    assert "Backend mission preview failed" in text
    assert "backend_mission_preview_failed" in text
    assert "No live external side effects were performed." in text
