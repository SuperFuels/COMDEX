from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.marketing_connection_service import MarketingConnectionService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _store(tmp_path) -> VaultDomainStore:
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    return VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"m" * 32),
        actor_id="marketing-test",
    )


def test_marketing_connection_and_metrics_survive_guardian_restart(tmp_path):
    store = _store(tmp_path)
    service = MarketingConnectionService(domain_store=store)
    service._write_record("acme", "linkedin", "connection", {
        "status": "connected", "provider": "linkedin", "permission_tier": "analytics",
        "granted_scopes": ["r_organization_admin"], "accounts": [],
        "selected_accounts": {}, "connected_by": "founder", "secret_ref": "keychain://redacted",
    }, actor_id="founder")
    service._write_record("acme", "linkedin", "metrics", {
        "schema_version": "aion.marketing.metrics.v1", "private": "customer analytics",
    }, actor_id="founder")

    restarted = MarketingConnectionService(domain_store=store)
    assert restarted.status("acme", "linkedin")["connected"] is True
    assert restarted.metrics("acme", "linkedin")["private"] == "customer analytics"
    assert not (tmp_path / ".runtime" / "AION_BUSINESS" / "business_containers" / "acme" / "integrations" / "marketing").exists()


def test_marketing_oauth_pending_state_is_vault_backed_and_single_use(monkeypatch, tmp_path):
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "client-private")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "secret-private")
    service = MarketingConnectionService(domain_store=_store(tmp_path))

    started = service.begin(
        "acme", "linkedin", tier="analytics", acting_person_id="founder",
    )
    state = parse_qs(urlparse(started["authorization_url"]).query)["state"][0]
    pending = service._locate_pending("linkedin", state)
    assert pending["workspace_id"] == "acme"
    service._consume_pending("linkedin", pending)

    with pytest.raises(ValueError, match="oauth_state_invalid_or_expired"):
        service._locate_pending("linkedin", state)
