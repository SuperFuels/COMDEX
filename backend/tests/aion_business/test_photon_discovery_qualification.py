from __future__ import annotations

from types import SimpleNamespace

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.photon_discovery_qualification import (
    build_photon_discovery_qualification_context,
    execute_photon_discovery_qualification,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_qualification_proves_exact_once_and_keeps_authority_outside_vault(
    tmp_path, monkeypatch,
):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"p" * 32)
    monkeypatch.setattr(
        "backend.modules.aion_business.runtime.photon_discovery_qualification.configured_business_vault_runtime",
        lambda: SimpleNamespace(guardian=guardian),
    )
    context = build_photon_discovery_qualification_context(
        secret_store_root=tmp_path / "secrets", export_root=tmp_path / "exports",
    )
    result = execute_photon_discovery_qualification(
        context, business_id="acme", endpoint="http://127.0.0.1:18096",
    )
    replay = execute_photon_discovery_qualification(
        context, business_id="acme", endpoint="http://127.0.0.1:18096",
    )
    assert result["grant"]["photons_granted"] == 1000
    assert result["grant_replay"]["replay"] is True
    assert result["reversal"]["photons_reversed"] == 100
    assert result["reversal_replay"]["replay"] is True
    assert replay["ledger_integrity"]["transaction_count"] == 4
    assert result["ledger_integrity"]["healthy"] is True
    assert result["billing_record"]["local_model_tokens_billed"] is False
    assert result["customer_content_included"] is False
    assert result["session"]["access_token"]
    assert context.wallet_public_key_path.is_relative_to(context.root)
    assert not context.root.is_relative_to(layout.root)
    assert (tmp_path / "exports" / "journey24-photon-billing-receipts.csv").exists()

    domains = VaultDomainStore(guardian)
    assert len(domains.list("finance.sales_records", workspace_id="acme")) == 1
    assert len(domains.list("train_agent.runs_and_audit", workspace_id="acme")) == 1
    assert len(domains.list("security.audit", workspace_id="acme")) == 1
    raw_vault = guardian.database.read_bytes()
    assert result["session"]["access_token"]["signature"].encode() not in raw_vault
    assert context.access_private_key.private_bytes_raw() not in raw_vault
