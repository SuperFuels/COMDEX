from __future__ import annotations

import base64

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_workflow.contracts_workflow_glyph import (
    WORKFLOW_SAVE_SCHEMA_VERSION,
)
from backend.modules.aion_workflow.workflow_approval_repository import (
    WorkflowApprovalRepository,
)
from backend.modules.aion_workflow.workflow_dry_run import dry_run_workflow_glyph
from backend.modules.aion_workflow.workflow_glyph_repository import (
    WorkflowGlyphRepository,
)
from backend.modules.aion_workflow.workflow_resume import (
    resume_workflow_after_approval,
)


def test_workflow_glyph_approval_and_audit_use_guardian_domains(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"w" * 32),
        actor_id="workflow-guardian-test",
    )
    legacy_root = tmp_path / "legacy-local-node"
    repository = WorkflowGlyphRepository(legacy_root, domain_store=store)
    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "acme",
        "workflow_id": "private_customer_follow_up",
        "name": "Private customer follow-up",
        "status": "draft",
        "graph": {
            "nodes": [
                {
                    "id": "manual",
                    "title": "Manual trigger",
                    "type": "Trigger",
                    "x": 0,
                    "y": 0,
                },
                {
                    "id": "draft",
                    "title": "Draft email for Private Client",
                    "type": "Action",
                    "x": 150,
                    "y": 0,
                },
                {
                    "id": "approval",
                    "title": "Human approval",
                    "type": "Gate",
                    "x": 300,
                    "y": 0,
                },
                {
                    "id": "send",
                    "title": "Send private customer email",
                    "type": "Action",
                    "x": 450,
                    "y": 0,
                },
            ],
            "edges": [
                {"from": "manual", "to": "draft", "condition": "success"},
                {"from": "draft", "to": "approval", "condition": "success"},
                {"from": "approval", "to": "send", "condition": "approved"},
            ],
        },
    }

    saved = repository.save(payload)
    assert saved["path"].startswith("vault://train_agent.automations/")
    assert not legacy_root.exists()

    # A fresh repository can recover the workflow solely from the Vault.
    restarted = WorkflowGlyphRepository(legacy_root, domain_store=store)
    record = restarted.load("acme", "private_customer_follow_up")
    assert record is not None
    assert record["name"] == "Private customer follow-up"

    dry_run = dry_run_workflow_glyph(
        workflow_record=record,
        audit_root=legacy_root,
        domain_store=store,
    )
    assert dry_run["audit_path"].startswith(
        "vault://train_agent.runs_and_audit/workflow_dry_runs/"
    )
    approval = dry_run["approval_request"]
    assert approval["path"].startswith(
        "vault://train_agent.runs_and_audit/workflow_approvals/"
    )

    approvals = WorkflowApprovalRepository(legacy_root, domain_store=store)
    approvals.decide(
        business_container="acme",
        workflow_id="private_customer_follow_up",
        approval_id=approval["approval_id"],
        decision="approved",
        reason="Founder approved the private customer message",
    )
    resumed = resume_workflow_after_approval(
        workflow_record=record,
        approval_id=approval["approval_id"],
        audit_root=legacy_root,
        domain_store=store,
    )
    assert resumed["audit_path"].startswith(
        "vault://train_agent.runs_and_audit/workflow_resume_runs/"
    )
    assert resumed["external_writes_performed"] is False
    assert not legacy_root.exists()
    assert store.guardian.verify_audit_chain()["healthy"] is True

    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private customer follow-up" not in database_bytes
    assert b"Private Client" not in database_bytes
    assert b"Founder approved the private customer message" not in database_bytes


def test_default_workflow_runtime_obeys_guardian_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vault_path = tmp_path / "external-customer-vault"
    settings = {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(vault_path),
        "TESSARIS_BUSINESS_NAME": "Acme",
        "TESSARIS_BUSINESS_STABLE_ID": "acme",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(
            b"e" * 32
        ).decode("ascii").rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)

    repository = WorkflowGlyphRepository()
    repository.save({
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "acme",
        "workflow_id": "environment_selected_workflow",
        "name": "Environment-selected private workflow",
        "status": "draft",
        "graph": {
            "nodes": [
                {
                    "id": "manual", "title": "Manual trigger",
                    "type": "Trigger", "x": 0, "y": 0,
                },
                {
                    "id": "approval", "title": "Human approval",
                    "type": "Gate", "x": 200, "y": 0,
                },
            ],
            "edges": [
                {"from": "manual", "to": "approval", "condition": "success"},
            ],
        },
    })
    record = WorkflowGlyphRepository().load("acme", "environment_selected_workflow")
    assert record is not None
    result = dry_run_workflow_glyph(workflow_record=record)
    assert result["audit_path"].startswith("vault://")
    assert result["approval_request"]["path"].startswith("vault://")
    assert not (tmp_path / ".runtime" / "local_node").exists()

    database_bytes = (vault_path / "records" / "guardian.sqlite3").read_bytes()
    assert b"Environment-selected private workflow" not in database_bytes
