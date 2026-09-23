from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def text() -> str:
    return APP.read_text()


def test_phase17j_bridge_exists() -> None:
    source = text()
    assert "PHASE 17J LOCK: Vault to Boardroom Gmail readiness bridge" in source
    assert "refreshAionPhase17JGmailVaultStatus" in source
    assert "window.testAionPhase17HGmailIntakeReadiness = refreshAionPhase17JGmailVaultStatus" in source


def test_phase17j_calls_real_local_vault_status_endpoint() -> None:
    source = text()
    assert "http://127.0.0.1:8080/api/vault/connectors/gmail/status" in source
    assert 'method: "GET"' in source


def test_phase17j_stores_vault_status_for_boardroom_readiness() -> None:
    source = text()
    assert "window.__aionGmailVaultStatus = payload" in source
    assert "state.gmailVaultStatus = payload" in source
    assert "window.__aionGmailOAuthReady = ready" in source


def test_phase17j_updates_visible_action_status() -> None:
    source = text()
    assert 'latest_action: "gmail_readiness_test"' in source
    assert 'readiness_status: ready ? "connected" : "missing"' in source
    assert "setAionPhase17HWebsiteIntakeActionState" in source


def test_phase17j_preserves_safe_policy() -> None:
    source = text()
    assert "raw_password_allowed: false" in source
    assert "password_auth_allowed: false" in source
    assert "live_send_allowed: false" in source
    assert "home_fixed@intake.tessaris.ai" not in source


def test_phase17j_is_in_focused_suite() -> None:
    suite = SUITE.read_text()
    assert "test_aion_phase17j_vault_boardroom_gmail_bridge_lock.py" in suite
