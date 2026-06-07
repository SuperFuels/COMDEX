from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21n_lock_marker_exists():
    assert "PHASE 21N LOCK: Pilot frontend interaction smoke" in TEXT


def test_phase21n_frontend_state_helpers_exist():
    assert "function getAionPilotFrontendInteractionState" in TEXT
    assert "function createAionPilotFrontendDraftMission" in TEXT
    assert "function renderAionPilotFrontendStreamEvents" in TEXT


def test_phase21n_create_draft_button_is_bound():
    assert 'target.closest("[data-aion-pilot-create-draft-mission]")' in TEXT
    assert "createAionPilotFrontendDraftMission();" in TEXT


def test_phase21n_button_updates_visible_status():
    assert 'pilotState.status = "draft_created"' in TEXT
    assert 'data-aion-pilot-status="${escapeHtml(snapshot.status)}"' in TEXT


def test_phase21n_stream_events_are_visible_not_private_reasoning():
    assert "data-aion-pilot-visible-stream-events" in TEXT
    assert "Draft mission created" in TEXT
    assert "getAionPilotOutputPreparedLabel(universalPlan)" in TEXT
    assert "getAionPilotOutputPreparedDetail(universalPlan)" in TEXT
    assert "Live external actions blocked" in TEXT
    assert "Private reasoning hidden." in TEXT


def test_phase21n_artifact_receipt_hashes_update_from_state():
    assert 'artifact_hash: pilotState.artifact_hash || "sha256:preview_artifact_hash"' in TEXT
    assert 'receipt_hash: pilotState.receipt_hash || "sha256:preview_receipt_hash"' in TEXT


def test_phase21n_replay_and_proof_hashes_visible():
    assert "Replay hash" in TEXT
    assert "Proof hash" in TEXT
    assert "sha256:frontend_draft_replay_preview" in TEXT
    assert "sha256:frontend_draft_proof_preview" in TEXT


def test_phase21n_no_forbidden_live_buttons():
    for forbidden in [
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
    ]:
        assert forbidden not in TEXT


def test_phase21n_no_raw_tool_execution_added():
    block_start = TEXT.index("PHASE 21N LOCK: Pilot frontend interaction smoke")
    block_end = TEXT.index("END PHASE 21N LOCK", block_start)
    block = TEXT[block_start:block_end]

    for forbidden in [
        "fetch(",
        "apiPost(",
        "window.open(",
        ".submit(",
        "sendEmail(",
        "deploySite(",
        "createPayment(",
        "payment_intent(",
        "stripe.",
        "revolut.",
    ]:
        assert forbidden not in block


def test_phase21n_safety_message_still_present():
    assert "AION stopped itself before doing anything risky." in TEXT
