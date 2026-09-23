from backend.modules.connectors.business_integration_catalog import get_business_integration_catalog


def test_catalog_separates_mailboxes_marketing_and_transactional_delivery(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_FROM_EMAIL", raising=False)
    catalog = get_business_integration_catalog()
    providers = {item["provider_id"]: item for item in catalog["providers"]}

    assert providers["gmail"]["category"] == "mailbox"
    assert providers["microsoft_outlook"]["category"] == "mailbox"
    assert providers["mailchimp_marketing"]["category"] == "marketing"
    assert providers["resend"]["category"] == "transactional_email"
    assert providers["twilio_messaging"]["category"] == "sms"
    assert providers["google_routes"]["category"] == "routing"
    assert providers["xero"]["category"] == "accounting"
    assert providers["freeagent"]["implementation"] == "adapter_ready"
    assert providers["freshbooks"]["implementation"] == "adapter_ready"
    assert providers["zoho_books"]["implementation"] == "adapter_ready"
    assert providers["hubspot"]["category"] == "crm"
    assert catalog["payments_deferred"] is True
    assert providers["resend"]["configured"] is False
    assert all(item["connected"] is False for item in catalog["providers"])


def test_catalog_reports_local_configuration_without_exposing_values(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "secret")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "hello@example.com")
    providers = {item["provider_id"]: item for item in get_business_integration_catalog()["providers"]}

    assert providers["resend"]["configured"] is True
    assert "secret" not in repr(providers["resend"])
