from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.governed_improvement_service import GovernedImprovementService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_governed_improvement_evidence_survives_guardian_restart_without_plaintext(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"i" * 32),
        actor_id="improvement-test",
    )
    legacy_root = tmp_path / "application" / "governed-improvement"
    service = GovernedImprovementService(
        legacy_root, workspace_id="acme", domain_store=store,
    )
    service.record_correction(
        correction_id="correction-private", task_class="sales_reply",
        target_ref="reply-1", corrected_value="Private customer wording",
        actor_id="founder",
    )
    service.record_outcome(
        outcome_id="outcome-private", task_class="sales_reply", route_id="local-model",
        procedure_id="professional-rewrite", verified=True, authority_ref="founder-review",
        score=0.95,
    )

    restarted = GovernedImprovementService(
        legacy_root, workspace_id="acme", domain_store=store,
    )
    changes = restarted.customer_changes()

    assert changes["count"] == 1
    assert restarted._records(restarted.corrections_path)[0]["correction_id"] == "correction-private"
    assert restarted._records(restarted.outcomes_path)[0]["outcome_id"] == "outcome-private"
    assert not legacy_root.exists()
    database = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"correction-private" not in database
    assert b"outcome-private" not in database
