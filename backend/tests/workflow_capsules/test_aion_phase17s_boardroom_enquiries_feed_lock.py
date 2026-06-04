from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")

def source() -> str:
    return APP.read_text()

def test_phase17s_boardroom_is_enquiries_feed_not_setup_wall() -> None:
    text = source()
    assert "PHASE 17S LOCK: Boardroom Website Enquiries Feed" in text
    assert "Website Enquiries Feed" in text
    assert "aion-enquiries-table" in text
    assert "Intake method" in text

def test_phase17s_uses_dropdown_and_single_selected_instruction_path() -> None:
    text = source()
    assert "data-aion-intake-provider-select" in text
    assert "selectedOption" in text
    assert "Advanced setup details" in text

def test_phase17s_main_view_has_feed_columns() -> None:
    text = source()
    for label in ["Time", "Customer", "Source", "Enquiry", "Status", "Next action", "Owner"]:
        assert f"<th>{label}</th>" in text

def test_phase17s_debug_controls_are_moved_to_advanced_drawer() -> None:
    text = source()
    advanced_idx = text.find("Advanced setup details")
    debug_idx = text.find("Check Gmail connection", advanced_idx)
    assert advanced_idx != -1
    assert debug_idx > advanced_idx

def test_phase17s_is_in_focused_suite() -> None:
    assert "test_aion_phase17s_boardroom_enquiries_feed_lock.py" in SUITE.read_text()
