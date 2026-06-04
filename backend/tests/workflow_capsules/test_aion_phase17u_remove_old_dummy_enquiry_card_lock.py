from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")

def source() -> str:
    return APP.read_text()

def test_old_home_fixed_dummy_quote_card_not_called() -> None:
    text = source()
    assert '${showHomeFixedIntakeQuote ? renderAionHomeFixedIntakeQuotePreview() : ""}' not in text
    assert "old standalone dummy enquiry card removed" in text

def test_founder_demo_visible_output_not_mounted_in_boardroom_main_flow() -> None:
    text = source()
    assert '${renderAionFounderDemoVisibleOutputPanel(state)}' not in text
    assert "founder demo visible output removed from Boardroom main flow" in text

def test_legacy_functions_can_remain_but_are_not_mounted() -> None:
    text = source()
    assert "function renderAionHomeFixedIntakeQuotePreview()" in text
    assert "function renderAionFounderDemoVisibleOutputPanel(state = {})" in text
    assert "renderAionHomeFixedIntakeQuotePreview() : " not in text

def test_enquiry_details_now_live_in_website_enquiries_feed() -> None:
    text = source()
    assert "Website Enquiries Feed" in text
    assert "data-aion-phase17t-enquiry-row" in text
    assert "data-aion-phase17t-enquiry-expanded" in text

def test_phase17u_is_in_focused_suite() -> None:
    assert "test_aion_phase17u_remove_old_dummy_enquiry_card_lock.py" in SUITE.read_text()
