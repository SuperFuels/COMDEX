from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def _text():
    return APP.read_text()


def _phase21f_block():
    text = _text()
    start = text.index("PHASE 21F LOCK: Read-only LRM Boardroom Projection Panel")
    end = text.index("END PHASE 21F LOCK", start)
    return text[start:end]


def _dashboard_block():
    text = _text()
    start = text.index("function renderBoardroomDashboardView")
    end = text.index("\nfunction ", start + 1)
    return text[start:end]


def test_phase21f_boardroom_projection_renderer_exists():
    text = _text()

    assert "function renderAionLrmBoardroomProjectionPanel" in text
    assert "data-aion-lrm-boardroom-projection-panel" in text
    assert "data-aion-phase21f-lrm-boardroom-projection" in text


def test_phase21f_boardroom_projection_reads_existing_pilot_lrm_state():
    block = _phase21f_block()

    assert "getAionPilotFrontendInteractionState()" in block
    assert "lrm_pilot_context_payload" in block
    assert "boardroom_projection" in block
    assert "lrm_state" in block
    assert "lrm_context_payload_hash" in block
    assert "lrm_next_review_state" in block
    assert "lrm_loop_hash" in block


def test_phase21f_boardroom_projection_mounted_in_existing_dashboard():
    block = _dashboard_block()

    assert "${renderAionLrmBoardroomProjectionPanel(snapshot)}" in block
    assert "renderBoardroomDashboardView" in block
    assert "renderBoardroomProofReplayPanel(snapshot)" in block


def test_phase21f_boardroom_projection_is_readonly_and_safe():
    block = _phase21f_block()

    assert "Read-only projection" in block
    assert "preview-only" in block
    assert "No booking, payment, escrow, external message, live chain write, workflow execution" in block

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


def test_phase21f_does_not_duplicate_boardroom_or_pilot_surfaces():
    block = _phase21f_block()

    assert "function renderBoardroomDashboardView" not in block
    assert "function renderBoardroomSurface" not in block
    assert "function renderAionPilotCockpitPanel" not in block
    assert "data-aion-pilot-cockpit" not in block
    assert "aion-pilot-stream-shell" not in block
