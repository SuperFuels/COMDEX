from __future__ import annotations

import json

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.retell_deployment_store import RetellDeploymentStore
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_retell_deployment_imports_then_restarts_from_guardian_without_plaintext(tmp_path):
    legacy = tmp_path / "retell_homefixed_agent.json"
    legacy.write_text(
        json.dumps({"workspace_id": "Home Fixed", "agent_id": "private-agent-123"}),
        encoding="utf-8",
    )
    layout = provision_business_vault(
        tmp_path / "vault",
        business_name="Home Fixed",
        business_stable_id="home-fixed",
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id="home-fixed", encryption_key=b"r" * 32
    )
    service = RetellDeploymentStore(
        domain_store=VaultDomainStore(guardian), legacy_path=legacy
    )

    assert service.read("Home Fixed")["agent_id"] == "private-agent-123"
    assert legacy.exists()
    service.write(
        {"workspace_id": "Home Fixed", "agent_id": "private-agent-456"},
        "Home Fixed",
    )

    restarted = RetellDeploymentStore(
        domain_store=VaultDomainStore(
            VaultGuardian(
                layout, business_stable_id="home-fixed", encryption_key=b"r" * 32
            )
        ),
        legacy_path=legacy,
    )
    assert restarted.read("Home Fixed")["agent_id"] == "private-agent-456"
    assert b"private-agent-456" not in (layout.records / "guardian.sqlite3").read_bytes()
