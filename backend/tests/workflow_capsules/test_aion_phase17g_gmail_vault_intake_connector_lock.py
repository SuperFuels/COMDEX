from pathlib import Path

APP = Path("desktop/mac/src/app.js")
TEXT = APP.read_text()


def test_phase17g_uses_gmail_vault_provider_not_fake_mailbox():
    assert "getAionPhase17GGmailVaultReadiness" in TEXT
    assert "Gmail OAuth from Vault" in TEXT
    assert "Vault OAuth" in TEXT
    assert "vault.gmail.credentials" in TEXT
    assert "No raw passwords" in TEXT
    assert "home_fixed@intake.tessaris.ai" not in TEXT


def test_phase17g_exposes_honest_provider_routes():
    assert "Hosted AION Mailbox" in TEXT
    assert "future_paid_route" in TEXT
    assert "Existing Form Webhook" in TEXT
    assert "AION Generated Form / Embed" in TEXT
    assert "future_no_code" in TEXT


def test_phase17g_boardroom_actions_are_not_fake_copy_email():
    assert "Check Gmail connection" in TEXT or "Test Gmail intake readiness" in TEXT
    assert "Copy webhook endpoint" in TEXT
    assert "Copy future embed snippet" in TEXT
    assert "Send local dummy payload" in TEXT or "Send local payload test" in TEXT
    assert "Copy intake email" not in TEXT


def test_phase17g_gmail_missing_routes_user_to_vault():
    assert "Connect Gmail in Vault before testing real email intake." in TEXT
    assert "Open Vault to connect Gmail" in TEXT
    assert "gmail_oauth_missing" in TEXT
    assert "vault_missing" in TEXT


def test_phase17g_gmail_connected_prepares_real_readiness_state():
    assert "gmail_vault_ready" in TEXT
    assert "pending_real_gmail_message_selection" in TEXT
    assert "Gmail Vault credential is ready for guarded intake read testing." in TEXT


def test_phase17g_preserves_side_effect_guards():
    assert "live_send_allowed: false" in TEXT
    assert "raw_password_allowed: false" in TEXT
    assert "human_review_required: true" in TEXT
    assert "Live send locked" in TEXT


def test_phase17g_installation_panel_still_mounted():
    assert "${renderAionWebsiteIntakeInstallationPanel()}" in TEXT
    assert "Connect Your Website Enquiries" in TEXT
    assert "data-aion-phase17f-website-intake-installation" in TEXT


def test_phase17g_reuses_phase17_live_test_state_panel():
    assert "getAionPhase17GLiveTestState" in TEXT
    assert "latest_submission" in TEXT
    assert "renderAionPhase17G" in TEXT

def test_phase17g_gmail_vault_readiness_does_not_require_global_state_binding() -> None:
    text = APP.read_text()
    start = text.index("function getAionPhase17GGmailVaultReadiness")
    end = text.index("function getAionPhase17GWebsiteIntakeProviders", start)
    block = text[start:end]

    assert 'typeof state !== "undefined"' in block
    assert "window.__aionState || window.state || {}" in block
    assert "const vault =" in block
    assert "appState?.vault" in block
    assert "appState?.vaultCredentials" in block
    assert "window.__aionVault" in block
    assert "const vault = state?.vault" not in block

