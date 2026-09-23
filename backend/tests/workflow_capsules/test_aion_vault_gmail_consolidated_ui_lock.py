from pathlib import Path

APP = Path("desktop/mac/src/app.js")
ROUTER = Path("backend/api/local_node_router.py")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")

def source() -> str:
    return APP.read_text()

def test_vault_has_one_canonical_render_path() -> None:
    text = source()
    assert 'data-aion-vault-canonical-gmail-ui="true"' in text
    assert text.count("function renderVaultCredentialsSurface()") == 1
    assert "Connector status overview" not in text
    assert "HubSpot — planned" not in text
    assert "Mailchimp — planned" not in text

def test_vault_no_stacked_l_m_n_overlay_blocks() -> None:
    text = source()
    assert "PHASE 17L LOCK: simplified Vault connector UX" not in text
    assert "PHASE 17M LOCK: final Vault Gmail connect UX binding" not in text
    assert "PHASE 17M LOCK: final simplified Vault UX" not in text
    assert "PHASE 17N LOCK: Gmail OAuth success refresh bridge" not in text

def test_vault_keeps_single_phase17k_handler_source() -> None:
    text = source()
    assert text.count("function installAionPhase17KDelegatedBindings()") == 1
    assert "gmail_already_connected" in text

def test_oauth_success_page_is_terminal_not_reconnect_loop() -> None:
    text = ROUTER.read_text()
    block = text[text.find("html = f"):text.find("@router.post", text.find("html = f"))]
    assert "Return to the Tessaris app" in block
    assert "aion:gmail_oauth_connected" in block
    assert "setTimeout(function" not in block
    assert "window.close()" not in block

def test_consolidation_test_is_in_focused_suite() -> None:
    assert "test_aion_vault_gmail_consolidated_ui_lock.py" in SUITE.read_text()

def test_vault_final_layout_has_no_big_connected_button_and_shows_account() -> None:
    text = source()
    assert "aion-vault-connect-now-btn" in text
    assert "aion-vault-enable-live-btn" in text
    assert "Enable live" in text
    assert "Reconnect Gmail" in text
    assert "OAuth connected through Google · read-only intake enabled · live send locked." in text
    assert "live.email" in text
    assert "gmailVault.email" in text
    assert "Gmail account" in text
    assert "CONNECT NOW" not in text
    assert ">CONNECTED<" not in text

def test_vault_connect_now_button_is_compact_and_hard_bound() -> None:
    text = source()
    assert "aion-vault-connect-now-btn" in text
    assert "onclick=\"openAionPhase17KGmailOAuth()\"" in text
    assert "PHASE 17Q LOCK: Vault connect button click + compact width" in text
    assert "max-content !important" in text
    assert "width: auto !important" in text

