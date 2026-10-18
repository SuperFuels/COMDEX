from __future__ import annotations

from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.local_node.contracts_local_node import LocalNodeConfig
from backend.modules.local_node.guardian_train_task_stores import (
    GuardianTrainTaskApprovalStore,
    GuardianTrainTaskStore,
    configured_local_node_train_task_stores,
    migrate_local_node_train_task_stores,
)
from backend.modules.local_node.train_task_approval_store import TrainTaskApprovalStore
from backend.modules.local_node.train_task_store import TrainTaskStore


def _stores(tmp_path: Path):
    layout = provision_business_vault(
        tmp_path / "vault",
        business_name="Test Business",
        business_stable_id="business-one",
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id="business-one", encryption_key=b"t" * 32,
    )
    domains = VaultDomainStore(guardian, actor_id="train-task-test")
    return (
        guardian,
        GuardianTrainTaskStore("business-one", domains),
        GuardianTrainTaskApprovalStore("business-one", domains),
    )


def test_train_agent_local_node_state_round_trips_encrypted(tmp_path: Path) -> None:
    guardian, tasks, approvals = _stores(tmp_path)
    workflow = tasks.save_workflow(
        "business-one", "follow-up", {"instructions": "private workflow instructions"},
    )
    run = tasks.save_run(
        "business-one", "run-one", {"result": "private customer result"},
    )
    tasks.mark_seen("private-dedupe-key", {"customer": "Private Customer"})
    approval = approvals.save_approval(
        "business-one",
        "approval-one",
        {"status": "pending", "summary": "private approval content"},
    )

    assert tasks.get_workflow("business-one", "follow-up") == workflow
    assert tasks.list_runs("business-one") == [run]
    assert tasks.has_seen("private-dedupe-key") is True
    assert approvals.get_approval("business-one", "approval-one") == approval
    raw = guardian.database.read_bytes()
    for secret in (
        b"private workflow instructions",
        b"private customer result",
        b"Private Customer",
        b"private approval content",
    ):
        assert secret not in raw


def test_train_agent_migration_copies_verifies_and_retains_json(tmp_path: Path) -> None:
    config = LocalNodeConfig(
        node_id="node-one", workspace_id="business-one", base_dir=str(tmp_path / "legacy"),
    )
    source = TrainTaskStore(config.base_dir)
    source.save_workflow("business-one", "workflow-one", {"steps": ["one"]})
    source.save_run("business-one", "run-one", {"status": "complete"})
    source.mark_seen("dedupe-one", {"run_id": "run-one"})
    source_approvals = TrainTaskApprovalStore(config.base_dir)
    source_approvals.save_approval(
        "business-one", "approval-one", {"status": "pending"},
    )
    source_files = sorted(Path(config.base_dir).rglob("*.json"))
    _, task_target, approval_target = _stores(tmp_path / "target")

    receipt = migrate_local_node_train_task_stores(
        config, task_target=task_target, approval_target=approval_target,
    )

    assert receipt["copied_and_verified"] == {
        "workflows": 1, "runs": 1, "approvals": 1, "dedupe": 1,
    }
    assert receipt["source_retained"] is True
    assert all(path.exists() for path in source_files)


def test_train_agent_plaintext_store_is_forbidden_in_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    config = LocalNodeConfig(
        node_id="node-one", workspace_id="business-one", base_dir=str(tmp_path / "node"),
    )

    with pytest.raises(RuntimeError, match="guardian_train_task_store_required"):
        configured_local_node_train_task_stores(config)
