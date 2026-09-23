from pathlib import Path

APP = Path("desktop/mac/src/app.js")
ROUTER = Path("backend/api/local_node_router.py")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")

def source() -> str:
    return APP.read_text()

def test_phase17n_installs_oauth_success_refresh_bridge() -> None:
    text = source()
    assert "PHASE 17N LOCK: Gmail OAuth success refresh bridge" in text
    assert "aion:gmail_oauth_connected" in text
    assert "window.addEventListener(\"focus\"" in text
    assert "refreshAionPhase17NGmailOAuthSuccess" in text

def test_phase17n_success_page_notifies_opener_and_auto_closes() -> None:
    text = ROUTER.read_text()
    assert "window.opener.postMessage" in text
    assert "aion:gmail_oauth_connected" in text
    assert "window.close()" in text
    assert "Gmail connected" in text

def test_phase17n_connected_button_does_not_look_like_reconnect_loop() -> None:
    text = source()
    assert "GMAIL CONNECTED" in text
    assert "CONNECT GMAIL WITH OAUTH" in text
    assert "connector_health === \"available\"" in text

def test_phase17n_is_in_focused_suite() -> None:
    suite = SUITE.read_text()
    assert "test_aion_phase17n_gmail_oauth_success_refresh_lock.py" in suite
