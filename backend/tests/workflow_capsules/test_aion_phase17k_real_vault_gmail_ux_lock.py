from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def text() -> str:
    return APP.read_text()


def test_phase17k_lock_markers_exist() -> None:
    source = text()
    assert "PHASE 17K LOCK: Real Vault Gmail connector UX + Boardroom poll bridge" in source
    assert "END PHASE 17K LOCK" in source


def test_phase17k_vault_has_real_connector_selector() -> None:
    source = text()
    assert "data-aion-phase17k-real-vault-connector-ux" in source
    assert "Connect app to Vault" in source
    assert "data-aion-phase17k-category-select" in source
    assert "data-aion-phase17k-app-select" in source
    assert "Gmail / Google Workspace" in source


def test_phase17k_gmail_connect_calls_real_connect_url() -> None:
    source = text()
    assert "openAionPhase17KGmailOAuth" in source
    assert "/api/local-node/connectors/gmail/connect-url" in source
    assert "window.open(connectUrl" in source
    assert "consent_pending" in source


def test_phase17k_gmail_health_calls_local_node_source_of_truth() -> None:
    source = text()
    assert "refreshAionPhase17KGmailHealth" in source
    assert "/api/local-node/connectors/gmail/health" in source
    assert "auth_status" in source
    assert "connector_health" in source
    assert 'authStatus === "connected"' in source


def test_phase17k_gmail_poll_now_calls_real_poll_endpoint() -> None:
    source = text()
    assert "pollAionPhase17KGmailNow" in source
    assert "/api/local-node/train-tasks/gmail/poll-now" in source
    assert "matched" in source
    assert "skipped" in source
    assert "deduped" in source
    assert "gmail_live_readonly" in source


def test_phase17k_preserves_safety_locks() -> None:
    source = text()
    assert "OAuth only" in source
    assert "no raw passwords" in source
    assert "dry-run only" in source
    assert "live send locked" in source
    assert "external_writes_enabled" in source


def test_phase17k_boardroom_intake_has_clear_buttons() -> None:
    source = text()
    assert "Check Gmail connection" in source
    assert "Open Gmail OAuth" in source
    assert "Poll Gmail now" in source
    assert "Send local dummy payload" in source


def test_phase17k_phase17g_readiness_uses_local_node_health() -> None:
    source = text()
    start = source.index("function getAionPhase17GGmailVaultReadiness()")
    end = source.index("function getAionPhase17GWebsiteIntakeProviders", start)
    block = source[start:end]
    assert "window.__aionGmailHealth" in block
    assert "getAionPhase17KConnectorState" in block
    assert "Local Node OAuth" in block
    assert "localConnected" in block


def test_phase17k_delegated_bindings_installed() -> None:
    source = text()
    assert "installAionPhase17KDelegatedBindings" in source
    assert "data-aion-phase17k-open-gmail-oauth" in source
    assert "data-aion-phase17k-refresh-gmail-health" in source
    assert "data-aion-phase17k-poll-gmail-now" in source
    assert "document.addEventListener" in source


def test_phase17k_is_in_focused_suite() -> None:
    suite = SUITE.read_text()
    assert "test_aion_phase17k_real_vault_gmail_ux_lock.py" in suite

def test_phase17k_vault_status_bridges_local_node_gmail_health() -> None:
    source = Path("backend/api/vault_router.py").read_text()
    assert "get_runtime().get_gmail_connector_health()" in source
    assert "local_node_gmail_connected" in source
    assert "source\": \"local_node_gmail_health\"" in source or "local_node_gmail_health" in source
    assert "dry_run_only" in source
    assert "external_writes_enabled" in source
    assert "live_send_enabled" in source
