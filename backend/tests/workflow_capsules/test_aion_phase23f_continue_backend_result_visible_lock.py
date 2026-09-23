from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_phase23f_continue_runner_adds_visible_loading_output():
    text = APP.read_text()

    start = text.index("async function runAionPilotSafeWorkPreview")
    end = text.index("/* END PHASE 21T LOCK */", start)
    block = text[start:end]

    assert "Loading backend mission map" in block
    assert "/api/local-node/aion/pilot/mission-preview" in block
    assert "frontend_backend_mission_map_loading" in block
    assert "requestRender()" in block


def test_phase23f_continue_runner_logs_backend_payload_and_result():
    text = APP.read_text()

    assert "[AION Pilot] Fetching backend mission preview" in text
    assert "[AION Pilot] Backend mission preview received" in text
    assert "[AION Pilot] Mission map output appended" in text
    assert "[AION Pilot] Backend mission preview runner failed" in text
