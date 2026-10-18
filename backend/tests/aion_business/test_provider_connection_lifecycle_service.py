from __future__ import annotations

import os

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.provider_connection_lifecycle_service import (
    ProviderConnectionLifecycleService,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_connect_refresh_revoke_and_reconnect_keep_authority_outside_vault(monkeypatch, tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"p" * 32)
    domains = VaultDomainStore(guardian)
    secret_root = tmp_path / "security"
    monkeypatch.setenv("TESSARIS_PROVIDER_SECRET_STORE_DIR", str(secret_root))
    service = ProviderConnectionLifecycleService(domain_store=domains)

    connected = service.connect(
        "acme", "xero", authority={"access_token": "access-one", "refresh_token": "refresh-one"},
        actor_id="person.owner", granted_scopes=["accounting.settings.read", "offline_access"],
        provider_account_hash="sha256:provider-account",
    )
    assert connected["connected"] is True
    assert connected["generation"] == 1
    assert connected["raw_tokens_exposed"] is False
    assert "access-one" not in repr(connected)
    secret_file = next(secret_root.glob("*.authority.json"))
    assert os.stat(secret_file).st_mode & 0o777 == 0o600
    assert b"access-one" not in guardian.database.read_bytes()

    refreshed = service.refresh(
        "acme", "xero", authority={"access_token": "access-two", "refresh_token": "refresh-two"},
        actor_id="person.owner",
    )
    assert refreshed["connected"] is True
    assert refreshed["last_refresh_at"]
    assert "access-two" not in repr(refreshed)
    assert b"access-two" not in guardian.database.read_bytes()

    revoked = service.revoke("acme", "xero", actor_id="person.owner")
    assert revoked["status"] == "revoked"
    assert revoked["connected"] is False
    assert revoked["authority_present"] is False
    assert not secret_file.exists()
    with pytest.raises(PermissionError, match="reconnect_required"):
        service.refresh(
            "acme", "xero", authority={"access_token": "invalid-after-revoke"},
            actor_id="person.owner",
        )

    reconnected = service.connect(
        "acme", "xero", authority={"access_token": "access-three", "refresh_token": "refresh-three"},
        actor_id="person.owner", granted_scopes=["offline_access"],
        provider_account_hash="sha256:provider-account",
    )
    assert reconnected["connected"] is True
    assert reconnected["generation"] == 2

    restarted = ProviderConnectionLifecycleService(domain_store=domains)
    assert restarted.status("acme", "xero")["generation"] == 2
    assert len(domains.list("finance.integration_records", workspace_id="acme")) == 1
    assert len(domains.list("departments.operational_records", workspace_id="acme")) == 1
    receipts = domains.list("security.audit", workspace_id="acme")
    event_types = [row["payload"]["event_type"] for row in receipts]
    assert len(event_types) == 4
    assert event_types.count("connected") == 2
    assert set(event_types) == {"connected", "refreshed", "revoked"}
    database = guardian.database.read_bytes()
    for secret in (b"access-one", b"refresh-one", b"access-two", b"refresh-two", b"access-three", b"refresh-three"):
        assert secret not in database
