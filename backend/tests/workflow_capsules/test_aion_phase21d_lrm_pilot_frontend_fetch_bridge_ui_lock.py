from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def _text():
    return APP.read_text()


def _block():
    text = _text()
    start = text.index("PHASE 21D LOCK: LRM Pilot Context Preview Fetch Bridge")
    end = text.index("END PHASE 21D LOCK", start)
    return text[start:end]


def test_phase21d_fetch_bridge_functions_exist():
    text = _text()

    assert "function getAionLrmPilotContextPreviewUrl" in text
    assert "function applyAionLrmPilotContextPreviewPayload" in text
    assert "async function fetchAionLrmPilotContextPreviewIntoPilotState" in text
    assert "window.fetchAionLrmPilotContextPreviewIntoPilotState" in text


def test_phase21d_uses_phase21c_local_endpoint():
    block = _block()

    assert "/api/local-node/aion/lrm/pilot-context-preview" in block
    assert "business_id" in block
    assert "mission_id" in block
    assert "mission_run_id" in block
    assert "fetch(url" in block
    assert 'method: "GET"' in block


def test_phase21d_applies_payload_to_existing_pilot_state():
    block = _block()

    assert "getAionPilotFrontendInteractionState()" in block
    assert "lrm_pilot_context_payload" in block
    assert "lrm_context_payload_hash" in block
    assert "lrm_next_review_state" in block
    assert "replay_hash" in block
    assert "proof_hash" in block
    assert "artifact_hash" in block
    assert "receipt_hash" in block
    assert "visible_stream_events" in block


def test_phase21d_create_draft_mission_fetches_lrm_context():
    text = _text()

    start = text.index("function createAionPilotFrontendDraftMission")
    end = text.index("\nfunction ", start + 1)
    block = text[start:end]

    assert "fetchAionLrmPilotContextPreviewIntoPilotState" in block
    assert 'business_id: "home-fixed"' in block
    assert 'mission_id: "pilot_demo_pdf_mission"' in block
    assert 'mission_run_id: "pilot_demo_run_preview"' in block


def test_phase21d_does_not_create_duplicate_pilot_or_live_actions():
    block = _block()

    forbidden = [
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
        "createEscrow",
        "releaseFunds",
        "sendExternalMessage",
        "executeWorkflow",
        "writeLiveChain",
    ]

    for term in forbidden:
        assert term not in block


def test_phase21d_is_fetch_bridge_not_ui_redesign():
    block = _block()

    assert "renderAionPilotCockpitPanel" not in block
    assert "renderAionPilotSimpleTaskStream" not in block
    assert "aion-pilot-stream-shell" not in block
    assert "data-aion-pilot-cockpit" not in block
