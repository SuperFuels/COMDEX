from __future__ import annotations

import base64

from backend.modules.aion_agents.contracts.approval_request import ApprovalRequest
from backend.modules.aion_agents.contracts.workflow_run import WorkflowRun
from backend.modules.aion_agents.runtime.agent_definition_repository import (
    AgentDefinitionRepository,
)
from backend.modules.aion_agents.runtime.approval_request_repository import (
    ApprovalRequestRepository,
)
from backend.modules.aion_agents.runtime.marketing_operator_seed import (
    build_marketing_seed_bundle,
)
from backend.modules.aion_agents.runtime.trigger_definition_repository import (
    TriggerDefinitionRepository,
)
from backend.modules.aion_agents.runtime.workflow_definition_repository import (
    WorkflowDefinitionRepository,
)
from backend.modules.aion_agents.runtime.workflow_run_repository import (
    WorkflowRunRepository,
)
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.local_node.contracts_local_node import LocalNodeConfig
from backend.modules.local_node.local_node_runtime import LocalNodeRuntime


def test_all_legacy_agent_repositories_use_encrypted_train_agent_domains(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"a" * 32),
        actor_id="agent-repository-test",
    )
    workspace_id = "acme"
    legacy_root = tmp_path / "legacy-runtime"
    workflows = WorkflowDefinitionRepository(legacy_root, domain_store=store)
    agents = AgentDefinitionRepository(legacy_root, domain_store=store)
    triggers = TriggerDefinitionRepository(legacy_root, domain_store=store)
    runs = WorkflowRunRepository(legacy_root, domain_store=store)
    approvals = ApprovalRequestRepository(legacy_root, domain_store=store)

    bundle = build_marketing_seed_bundle(workspace_id)
    bundle["workflow"].name = "Private launch campaign"
    workflows.save(bundle["workflow"])
    agents.save(bundle["agent"])
    triggers.save(bundle["trigger"])

    run = WorkflowRun(
        id="run_private_launch",
        workspace_id=workspace_id,
        workflow_id=bundle["workflow"].id,
        workflow_name="Private launch campaign",
        status="waiting_approval",
        input_payload={"brief": "Confidential customer acquisition plan"},
        created_at="2026-10-17T00:00:00+00:00",
        updated_at="2026-10-17T00:00:00+00:00",
    )
    approval = ApprovalRequest(
        id="approval_private_launch",
        workspace_id=workspace_id,
        workflow_run_id=run.id,
        workflow_id=run.workflow_id,
        title="Approve confidential launch",
        requested_action={"audience": "Private customer list"},
        requested_at="2026-10-17T00:00:00+00:00",
    )
    runs.save(run)
    approvals.save(approval)

    assert workflows.load(workspace_id, bundle["workflow"].id).name == "Private launch campaign"
    assert agents.load(workspace_id, bundle["agent"].id).id == bundle["agent"].id
    assert triggers.load(workspace_id, bundle["trigger"].id).id == bundle["trigger"].id
    assert runs.load(workspace_id, run.id).input_payload["brief"].startswith("Confidential")
    assert approvals.find_pending(workspace_id)[0].id == approval.id
    assert len(workflows.list_active(workspace_id)) == 1

    # Deletion is an auditable tombstone, not history destruction.
    assert triggers.delete(workspace_id, bundle["trigger"].id) is True
    assert triggers.get(workspace_id, bundle["trigger"].id) is None
    assert store.guardian.verify_audit_chain()["healthy"] is True

    assert not (legacy_root / "aion_agents").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private launch campaign" not in database_bytes
    assert b"Confidential customer acquisition plan" not in database_bytes
    assert b"Private customer list" not in database_bytes


def test_guardian_configured_local_node_never_seeds_plaintext_agent_files(
    tmp_path, monkeypatch
):
    vault_path = tmp_path / "customer-vault"
    application_root = tmp_path / "application"
    update_root = tmp_path / "updates"
    key = base64.urlsafe_b64encode(b"n" * 32).decode("ascii").rstrip("=")
    settings = {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(vault_path),
        "TESSARIS_BUSINESS_NAME": "Acme",
        "TESSARIS_BUSINESS_STABLE_ID": "acme",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": key,
        "TESSARIS_APPLICATION_ROOT": str(application_root),
        "TESSARIS_UPDATE_ROOT": str(update_root),
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)

    local_root = tmp_path / "local-node"
    runtime = LocalNodeRuntime(
        LocalNodeConfig(
            node_id="node-acme",
            workspace_id="acme",
            base_dir=str(local_root),
        )
    )

    assert runtime.workflow_definition_repository.vault is not None
    assert runtime.workflow_run_repository.vault is not None
    assert runtime.agent_definition_repository.vault is not None
    assert runtime.approval_request_repository.vault is not None
    assert runtime.trigger_definition_repository.vault is not None
    assert runtime.workflow_definition_repository.list_all("acme")
    assert runtime.agent_definition_repository.list_all("acme")
    assert runtime.trigger_definition_repository.list_all("acme")
    assert not (local_root / "aion_agents").exists()

    database_bytes = (vault_path / "records" / "guardian.sqlite3").read_bytes()
    assert b"Marketing Content Draft v1" not in database_bytes
