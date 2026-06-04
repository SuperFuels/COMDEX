from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")

def source() -> str:
    return APP.read_text()

def test_phase17t_rows_are_clickable_and_expand_inline() -> None:
    text = source()
    assert "PHASE 17T LOCK: clickable Website Enquiries Feed rows" in text
    assert "data-aion-phase17t-enquiry-row" in text
    assert "data-aion-phase17t-enquiry-expanded" in text
    assert "setAionPhase17TSelectedWebsiteEnquiry" in text

def test_phase17t_expanded_enquiry_contains_workflow_preview_details() -> None:
    text = source()
    assert "New website enquiry" in text
    assert "Pergola / roof repair" in text
    assert "Workflow preview ready" in text
    assert "Run workflow preview" in text
    assert "Approve next action" in text
    assert "Request more info" in text

def test_phase17t_expanded_enquiry_has_close_and_safe_mode() -> None:
    text = source()
    assert "Close" in text
    assert "Safe mode: no booking, payment, escrow, external message, or chain write. Human review required." in text
    assert "Show technical trace" in text

def test_phase17t_old_dummy_enquiry_card_is_hidden() -> None:
    text = source()
    assert "PHASE 17T LOCK: enquiry details live inside Website Enquiries Feed" in text
    assert "data-aion-home-fixed-demo-enquiry" in text
    assert "display: none !important" in text

def test_phase17t_is_in_focused_suite() -> None:
    assert "test_aion_phase17t_clickable_enquiry_rows_lock.py" in SUITE.read_text()
