from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def source() -> str:
    return APP.read_text()


def test_phase17m_final_connect_binding_is_installed() -> None:
    text = source()
    assert "installAionPhase17MFinalVaultConnectBinding" in text
    assert "data-aion-phase17m-connect-gmail" in text
    assert "openAionPhase17KGmailOAuth" in text


def test_phase17m_final_vault_styles_are_js_safe() -> None:
    text = source()
    assert "installAionPhase17MFinalVaultUxStyles" in text
    assert "aion-phase17m-final-vault-ux-style" in text
    assert "style.textContent" in text


def test_phase17m_hides_old_diagnostic_vault_panels() -> None:
    text = source()
    assert ".operations-agents-metric-grid" in text
    assert ".operations-agents-two-column" in text
    assert ".vault-connector-list" in text
    assert "display: none !important" in text


def test_phase17m_keeps_clean_user_status_language() -> None:
    text = source()
    assert "OAuth connected through Google. Read-only intake enabled." in text
    assert "Safety: OAuth only · live send locked." in text


def test_phase17m_is_in_focused_suite() -> None:
    suite = SUITE.read_text()
    assert "test_aion_phase17m_final_vault_connect_ux_lock.py" in suite
