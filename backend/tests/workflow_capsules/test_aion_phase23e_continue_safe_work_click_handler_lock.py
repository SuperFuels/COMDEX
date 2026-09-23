from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_phase23e_dedicated_continue_safe_work_handler_exists():
    text = APP.read_text()

    assert "__aionPilotContinueSafeWorkClickHandlerInstalled" in text
    assert '[data-aion-pilot-continue-safe-work]' in text
    assert "runAionPilotSafeWorkPreview();" in text
    assert "Continue safe work clicked" in text


def test_phase23e_continue_handler_is_inside_phase23c_bridge():
    text = APP.read_text()

    start = text.index("PHASE 23C LOCK: Frontend Mission Preview Runtime Bridge")
    end = text.index("END PHASE 23C LOCK", start)
    block = text[start:end]

    assert "__aionPilotContinueSafeWorkClickHandlerInstalled" in block
    assert '[data-aion-pilot-continue-safe-work]' in block
    assert "event.stopPropagation();" in block
