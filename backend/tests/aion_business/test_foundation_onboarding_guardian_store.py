from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.foundation_onboarding_session_service import (
    FoundationOnboardingSessionService,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_onboarding_session_and_receipt_live_in_guardian(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"o" * 32)
    store = VaultDomainStore(guardian)
    service = FoundationOnboardingSessionService(domain_store=store)
    saved = service.save(
        "acme",
        packet={"transcript": [{"role": "user", "content": "Private founder detail"}]},
        expected_revision=0,
        actor_id="founder",
        device_id="macbook",
    )
    assert saved["revision"] == 1
    assert service.get("acme")["packet"]["transcript"][0]["content"] == "Private founder detail"
    assert len(store.list("onboarding.receipts", workspace_id="acme")) == 1
    assert b"Private founder detail" not in guardian.database.read_bytes()
