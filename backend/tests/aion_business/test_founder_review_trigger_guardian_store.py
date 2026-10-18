from __future__ import annotations

from unittest.mock import MagicMock

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.founder_review_trigger import FounderReviewTrigger
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_founder_review_trigger_survives_guardian_restart_without_plaintext_json(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"r" * 32),
        actor_id="founder-review-test",
    )
    dependencies = {
        "workspace_repository": MagicMock(), "role_repository": MagicMock(),
        "workflow": MagicMock(), "audit_log": MagicMock(), "resend_actions": MagicMock(),
    }
    trigger = FounderReviewTrigger(domain_store=store, **dependencies)
    trigger.get_or_create_config(
        workspace_id="acme", send_email=True,
        send_to_emails=["founder@private.test"], from_email="review@private.test",
    )
    trigger.update_config(
        workspace_id="acme", metadata={"private": "weekly founder decisions"}
    )

    restarted = FounderReviewTrigger(domain_store=store, **dependencies)
    loaded = restarted.load_config("acme")

    assert loaded.send_to_emails == ["founder@private.test"]
    assert loaded.metadata["private"] == "weekly founder decisions"
    assert not (tmp_path / ".runtime" / "AION_BUSINESS" / "founder_review_triggers" / "acme.json").exists()
    assert b"weekly founder decisions" not in (layout.records / "guardian.sqlite3").read_bytes()
