from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.finance_pilot_conversation_service import (
    FinancePilotConversationRepository,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_finance_pilot_conversation_restarts_from_encrypted_vault(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"q" * 32)
    domains = VaultDomainStore(guardian)
    repository = FinancePilotConversationRepository(domain_store=domains)
    session = repository.load("acme")
    session["turns"] = [{"role": "user", "content": "private cash-flow question"}]
    repository.save("acme", session)

    restarted = FinancePilotConversationRepository(domain_store=domains)
    assert restarted.load("acme")["turns"][0]["content"] == "private cash-flow question"
    assert b"private cash-flow question" not in guardian.database.read_bytes()
    assert not (tmp_path / "department_pilot_runtime").exists()
