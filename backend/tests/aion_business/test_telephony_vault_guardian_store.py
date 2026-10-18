from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.telephony_vault_service import TelephonyVaultService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_telephony_connection_metadata_survives_guardian_restart_without_plaintext(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"t" * 32),
        actor_id="telephony-test",
    )
    service = TelephonyVaultService(domain_store=store)
    service._write_metadata("acme", {
        "twilio": {"validated": True, "phone_number": "+34950000000"},
        "retell": {"validated": True, "agent_count": 2},
        "api_key_secret": "must-never-be-stored",
    })

    restarted = TelephonyVaultService(domain_store=store)
    metadata = restarted._metadata("acme")

    assert metadata["twilio"]["phone_number"] == "+34950000000"
    assert metadata["retell"]["agent_count"] == 2
    assert "api_key_secret" not in metadata
    assert b"+34950000000" not in (layout.records / "guardian.sqlite3").read_bytes()
