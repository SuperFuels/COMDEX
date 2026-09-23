from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21s_lock_marker_exists():
    assert "PHASE 21S LOCK: Pilot mission contract buttons" in TEXT


def test_phase21s_handlers_exist():
    for token in [
        "function approveAionPilotMissionContract",
        "function reviseAionPilotMissionContract",
        "function cancelAionPilotMissionContract",
        "function appendAionPilotStreamEvent",
    ]:
        assert token in TEXT


def test_phase21s_click_bindings_exist():
    for token in [
        'target.closest("[data-aion-pilot-feedback-approve]")',
        'target.closest("[data-aion-pilot-feedback-revise]")',
        'target.closest("[data-aion-pilot-feedback-stop]")',
    ]:
        assert token in TEXT


def test_phase21s_approve_sets_safe_work_only():
    assert 'pilotState.status = "approved_for_safe_work";' in TEXT
    assert 'pilotState.contract_status = "approved_for_safe_work";' in TEXT
    assert "Risky actions remain blocked until exact approval." in TEXT


def test_phase21s_revise_and_cancel_states_exist():
    assert 'pilotState.status = "revision_requested";' in TEXT
    assert 'pilotState.status = "cancelled";' in TEXT
    assert "Mission cancelled" in TEXT
    assert "Revision requested" in TEXT


def test_phase21s_contract_card_uses_status_copy():
    for token in [
        "Approved for safe work",
        "Revision requested",
        "Mission cancelled",
        "Draft contract ready",
    ]:
        assert token in TEXT


def test_phase21s_no_live_side_effects_added():
    phase_start = TEXT.index("PHASE 21S LOCK: Pilot mission contract buttons")
    phase_end = TEXT.index("END PHASE 21S LOCK", phase_start)
    block = TEXT[phase_start:phase_end]

    for forbidden in [
        "fetch(",
        "apiPost(",
        "sendEmail(",
        "deploySite(",
        "createPayment(",
        "stripe.",
        "revolut.",
    ]:
        assert forbidden not in block
