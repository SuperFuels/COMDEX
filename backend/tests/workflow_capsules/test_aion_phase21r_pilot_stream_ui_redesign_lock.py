from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21r_lock_marker_exists():
    assert "PHASE 21R LOCK: Pilot stream UI redesign" in TEXT
    assert "data-aion-phase21r-stream-ui-redesign" in TEXT


def test_phase21r_uses_stream_shell_and_bottom_composer():
    assert "aion-pilot-stream-shell" in TEXT
    assert "aion-pilot-stream-window" in TEXT
    assert "aion-pilot-composer-bar" in TEXT
    assert "grid-template-rows: auto minmax(420px, 1fr) auto" in TEXT
    assert "position: sticky" in TEXT
    assert "bottom: 0" in TEXT


def test_phase21r_cards_are_stream_containers():
    for token in [
        "data-aion-pilot-plan-card",
        "data-aion-pilot-contract-card",
        "data-aion-pilot-results-card",
        "data-aion-pilot-activity-card",
    ]:
        assert token in TEXT


def test_phase21r_main_input_is_in_composer_bar():
    start = TEXT.index("function renderAionPilotSimpleTaskStream")
    end = TEXT.index("function renderAionPilotAdvancedTechnicalDetails", start)
    block = TEXT[start:end]

    assert "data-aion-pilot-composer-bar" in block
    assert "data-aion-pilot-mission-input" in block
    assert "data-aion-pilot-create-draft-mission" in block


def test_phase21r_old_numbered_step_cards_not_in_simple_stream_function():
    start = TEXT.index("function renderAionPilotSimpleTaskStream")
    end = TEXT.index("function renderAionPilotAdvancedTechnicalDetails", start)
    block = TEXT[start:end]

    assert "aion-pilot-step-card" not in block
    assert "aion-pilot-step-number" not in block


def test_phase21r_advanced_details_remain_available():
    assert "Advanced details: proof, hashes, paths, lanes and blocked actions" in TEXT
    assert "renderAionPilotAdvancedTechnicalDetails(snapshot)" in TEXT


def test_phase21r_safety_message_retained():
    assert "AION stopped itself before doing anything risky." in TEXT
    assert "No posting, sending, payment, booking, escrow, deployment or ad spend without exact approval." in TEXT


def test_phase21r_result_buttons_still_present():
    for token in [
        "data-aion-pilot-open-output",
        "data-aion-pilot-download-output",
        "data-aion-pilot-view-receipt",
    ]:
        assert token in TEXT
