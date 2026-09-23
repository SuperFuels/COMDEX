from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "desktop/mac/src/styles.css").read_text(encoding="utf-8")


def test_vault_has_a_dedicated_provider_neutral_crm_panel():
    start = APP.index("function renderAionVaultCrmPanelV1")
    end = APP.index("if (!window.__aionVaultCrmHandlersV1Installed)", start)
    panel = APP[start:end]
    assert 'data-aion-vault-crm="true"' in panel
    assert "CRM / Sales evidence" in panel
    assert "normalized Sales evidence model" in panel
    for provider in ("HubSpot", "Salesforce", "Pipedrive", "Zoho CRM", "CSV / webhook / native"):
        assert provider in panel
    assert 'data-aion-vault-crm-provider-select="true"' in panel
    assert "selectedProvider" in panel
    assert "selectedIsHubSpot" in panel
    assert "No connection will be simulated" in panel


def test_hubspot_vault_controls_use_existing_backend_connector():
    start = APP.index("function getAionVaultCrmConnectorStateV1")
    end = APP.index("function renderVaultCredentialsSurface", start)
    crm = APP[start:end]
    assert "/api/local-node/connectors/hubspot/health" in crm
    assert "/api/local-node/connectors/hubspot/mcp/connect-url" in crm
    assert "/api/local-node/connectors/hubspot/disconnect" in crm
    assert "openExternalUrl" in crm
    assert "connect_url_generated" in crm
    assert "/placeholder|local[-_ ]?dev|example/i" in crm
    assert "!placeholder && authStatus" in crm
    assert "A local development placeholder exists, but no genuine HubSpot portal is connected" in crm


def test_crm_contract_is_read_only_and_write_actions_remain_gated():
    start = APP.index("function renderAionVaultCrmPanelV1")
    end = APP.index("if (!window.__aionVaultCrmHandlersV1Installed)", start)
    panel = APP[start:end]
    assert "Read-only evidence" in panel
    assert "Contacts, companies, lead sources, activity, deals, stages, quotes, won/lost outcomes" in panel
    assert "provider, source ID and sync time" in panel
    assert "Contact creation, stage changes, calls, emails, discounts and pricing remain approval-gated and receipt-backed" in panel
    assert "raw passwords and pasted private tokens are not requested" in panel


def test_crm_panel_is_rendered_inside_the_canonical_vault():
    start = APP.index("function renderVaultCredentialsSurface")
    end = APP.index("function getEditableBusinessContextFoundation", start)
    vault = APP[start:end]
    assert "renderAionVaultCrmPanelV1()" in vault
    assert vault.index("renderAionVaultCrmPanelV1()") < vault.index('data-aion-vault-canonical-gmail-ui="true"')


def test_crm_panel_has_responsive_vault_styling():
    for selector in (
        ".aion-vault-crm-panel",
        ".aion-vault-crm-provider-grid",
        ".aion-vault-crm-connection-row",
        ".aion-vault-crm-contract",
        ".aion-vault-crm-provider-select-row",
    ):
        assert selector in STYLES


def test_crm_provider_dropdown_changes_the_selected_provider_without_faking_availability():
    start = APP.index("if (!window.__aionVaultCrmHandlersV1Installed)")
    end = APP.index("function renderVaultCredentialsSurface", start)
    handlers = APP[start:end]
    assert 'data-aion-vault-crm-provider-select="true"' in handlers
    assert "selected_provider: String(select.value" in handlers
    panel = APP[APP.index("function renderAionVaultCrmPanelV1"):start]
    assert "Connector not installed" in panel
    assert "Import route not installed" in panel
    assert "disabled" in panel
