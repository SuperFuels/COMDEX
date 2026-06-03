from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def source() -> str:
    return APP.read_text()


def test_phase17l_simple_vault_panel_exists() -> None:
    text = source()
    assert "renderAionPhase17LSimpleVaultConnectorPanel" in text
    assert "data-aion-phase17l-simple-vault-ui" in text
    assert "Connect app to Vault" in text


def test_phase17l_has_simple_category_app_connect_flow() -> None:
    text = source()
    assert "data-aion-phase17l-category" in text
    assert "data-aion-phase17l-app" in text
    assert "Gmail / Google Workspace" in text
    assert "data-aion-phase17k-open-gmail-oauth" in text
    assert "Reconnect" in text
    assert "Connect" in text


def test_phase17l_shows_clear_connected_status_only() -> None:
    text = source()
    assert "data-aion-phase17l-gmail-status" in text
    assert "Read-only intake enabled · Live send locked" in text
    assert "aion-vault-status-dot" in text


def test_phase17l_moves_technical_controls_to_advanced_details() -> None:
    text = source()
    assert "Advanced details" in text
    assert "data-aion-phase17k-refresh-gmail-health" in text
    assert "data-aion-phase17k-poll-gmail-now" in text


def test_phase17l_hides_dummy_future_connectors_from_main_path() -> None:
    text = source()
    assert "installAionPhase17LSimplifiedVaultStyles" in text
    assert "vault-connector-list .vault-connector-row:nth-child(n+3)" in text
    assert "display: none" in text


def test_phase17l_is_in_focused_suite() -> None:
    suite = SUITE.read_text()
    assert "test_aion_phase17l_simplified_vault_connector_ui_lock.py" in suite
