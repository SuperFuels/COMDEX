from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")

def source() -> str:
    return APP.read_text()

def test_phase18_reframes_founder_demo_as_a2a_commercial_ticket() -> None:
    text = source()
    assert "PHASE 18 LOCK: Universal A2A Commercial Ticket model" in text
    assert "A2A Job / Order Ticket" in text
    assert "Universal route for products, hourly work" in text
    assert "function renderBoardroomFounderDemoLoopPanel(snapshot = {})" in text
    assert "return renderAionPhase18CommercialTicketPanel();" in text

def test_phase18_has_universal_commercial_routes() -> None:
    text = source()
    for route in ["hourly_service", "discovery_session", "custom_quote", "fixed_product", "metered_work"]:
        assert route in text

def test_phase18_replaces_fake_quote_with_commercial_route() -> None:
    text = source()
    block = text[text.find("PHASE 18 LOCK"):text.find("END PHASE 18 LOCK")]
    assert "Commercial route selected" in block
    assert "not a fake final quote" in block
    assert "Quote preview generated" not in block

def test_phase18_models_calendar_resource_availability() -> None:
    text = source()
    assert "requires_calendar" in text
    assert "single_engineer_now_multi_engineer_ready_later" in text
    assert "requested_slot" in text
    assert "available_slot" in text
    assert "live_booking_created: false" in text

def test_phase18_keeps_guarded_no_side_effect_contract() -> None:
    text = source()
    for guard in [
        "booking_created: false",
        "payment_created: false",
        "escrow_created: false",
        "external_message_sent: false",
        "live_chain_write: false",
        "human_review_required",
        "preview_only",
    ]:
        assert guard in text

def test_phase18_has_clean_ui_and_advanced_trace() -> None:
    text = source()
    assert "aion-phase18-ticket-summary" in text
    assert "aion-phase18-timeline" in text
    assert "aion-phase18-proposal-grid" in text
    assert "Advanced technical trace" in text
    assert "installAionPhase18A2ATicketStyles" in text

def test_phase18_is_in_focused_suite() -> None:
    assert "test_aion_phase18_a2a_commercial_ticket_lock.py" in SUITE.read_text()
