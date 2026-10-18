from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def _text():
    return APP.read_text()


def _phase21e_block():
    text = _text()
    start = text.index("PHASE 21E LOCK: Read-only LRM context card in existing Pilot stream")
    end = text.index("END PHASE 21E LOCK", start)
    return text[start:end]


def _simple_stream_block():
    text = _text()
    start = text.index("function renderAionPilotSimpleTaskStream")
    end = text.index("/* END PHASE 21R LOCK */", start)
    return text[start:end]


def test_phase21e_readonly_lrm_context_card_renderer_exists():
    text = _text()

    assert "function renderAionLrmPilotContextReadonlyCard" in text
    assert "data-aion-lrm-pilot-context-card" in text
    assert "data-aion-phase21e-lrm-readonly-card" in text


def test_phase21e_card_reads_existing_pilot_state_only():
    block = _phase21e_block()

    assert "getAionPilotFrontendInteractionState()" in block
    assert "lrm_pilot_context_payload" in block
    assert "lrm_context_payload_hash" in block
    assert "lrm_next_review_state" in block
    assert "lrm_loop_hash" in block
    assert "replay_hash" in block
    assert "visible_stream_events" in block


def test_phase21e_card_mounted_inside_existing_pilot_stream():
    block = _simple_stream_block()

    assert "${renderAionLrmPilotContextReadonlyCard(pilotState)}" in block
    assert "renderAionPilotSimpleTaskStream" in block


def test_phase21e_card_is_readonly_and_safe():
    block = _phase21e_block()

    assert "read-only" in block
    assert "Preview-only" in block
    assert "No booking, payment, escrow, external message, live chain write or workflow execution" in block

    forbidden = [
        "fetch(",
        "apiPost",
        "createEscrow",
        "releaseFunds",
        "sendExternalMessage",
        "executeWorkflow",
        "writeLiveChain",
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
    ]

    for term in forbidden:
        assert term not in block


def test_phase21e_card_does_not_duplicate_pilot_surface():
    block = _phase21e_block()

    assert "data-aion-pilot-cockpit" not in block
    assert "renderAionPilotCockpitPanel" not in block
    assert "renderAionPilotSimpleTaskStream" not in block
    assert "aion-pilot-stream-shell" not in block
