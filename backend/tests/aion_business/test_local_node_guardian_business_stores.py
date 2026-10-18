from __future__ import annotations

import base64
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.department_operational_store import (
    BusinessOperationsRecordRepository,
    DepartmentOperationalStore,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.local_node.contracts_local_node import (
    ApprovalRecord,
    AuditEvent,
    LocalNodeConfig,
    QueueItem,
)
from backend.modules.local_node.guardian_business_stores import (
    GuardianLocalApprovalStore,
    GuardianLocalAuditStore,
    GuardianLocalQueueStore,
    configured_local_node_business_stores,
    migrate_local_node_business_stores,
)
from backend.modules.local_node.local_approval_store import LocalApprovalStore
from backend.modules.local_node.local_audit_store import LocalAuditStore
from backend.modules.local_node.local_queue_store import LocalQueueStore


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _guardian_stores(tmp_path: Path, workspace_id: str = "business-one"):
    layout = provision_business_vault(
        tmp_path / "vault",
        business_name="Test Business",
        business_stable_id=workspace_id,
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id=workspace_id, encryption_key=b"v" * 32,
    )
    domains = VaultDomainStore(guardian, actor_id="local-node-test")
    operational = DepartmentOperationalStore(domain_store=domains)
    return (
        guardian,
        GuardianLocalQueueStore(
            workspace_id,
            BusinessOperationsRecordRepository(
                "local_node_queue", operational_store=operational,
            ),
        ),
        GuardianLocalApprovalStore(
            workspace_id,
            BusinessOperationsRecordRepository(
                "local_node_approvals", operational_store=operational,
            ),
        ),
        GuardianLocalAuditStore(workspace_id, operational),
    )


def _records(workspace_id: str = "business-one"):
    queue = QueueItem.new(
        workspace_id=workspace_id,
        workflow_id="send-private-proposal",
        operator_id="operator-one",
        department_key="sales",
        payload={"customer_note": "confidential queue content"},
    )
    approval = ApprovalRecord.new(
        workspace_id=workspace_id,
        run_id="run-one",
        operator_id="operator-one",
        department_key="sales",
        title="Approve customer proposal",
        summary="confidential approval summary",
        payload={"recipient": "private@example.test"},
        queue_item_id=queue.id,
    )
    audit = AuditEvent.new(
        node_id="node-one",
        workspace_id=workspace_id,
        event_type="proposal_prepared",
        level="info",
        message="confidential audit message",
        payload={"customer": "Private Customer"},
        queue_item_id=queue.id,
        approval_id=approval.id,
    )
    return queue, approval, audit


def test_local_node_business_records_round_trip_encrypted(tmp_path: Path) -> None:
    guardian, queues, approvals, audit = _guardian_stores(tmp_path)
    queue, approval, event = _records()

    queues.enqueue(queue)
    approvals.upsert(approval)
    audit.append(event)

    assert queues.get(queue.id).to_dict() == queue.to_dict()
    assert approvals.get(approval.id).to_dict() == approval.to_dict()
    assert audit.get(event.id).to_dict() == event.to_dict()
    assert queues.mark_running(queue.id, run_id="run-one").status == "running"
    assert approvals.resolve(
        approval.id, approve=True, resolved_by="founder",
    ).status == "approved"

    raw = guardian.database.read_bytes()
    for secret in (
        b"confidential queue content",
        b"confidential approval summary",
        b"private@example.test",
        b"confidential audit message",
        b"Private Customer",
    ):
        assert secret not in raw


def test_local_node_legacy_migration_copies_verifies_and_retains_source(tmp_path: Path) -> None:
    config = LocalNodeConfig(
        node_id="node-one", workspace_id="business-one", base_dir=str(tmp_path / "legacy"),
    )
    queue, approval, event = _records()
    LocalQueueStore(config.base_dir).enqueue(queue)
    LocalApprovalStore(config.base_dir).upsert(approval)
    LocalAuditStore(config.base_dir).append(event)
    source_paths = sorted(Path(config.base_dir).glob("*.sqlite3"))
    _, queue_target, approval_target, audit_target = _guardian_stores(tmp_path / "target")

    receipt = migrate_local_node_business_stores(
        config,
        queue_target=queue_target,
        approval_target=approval_target,
        audit_target=audit_target,
    )

    assert receipt["copied_and_verified"] == {"queue": 1, "approvals": 1, "audit": 1}
    assert receipt["source_retained"] is True
    assert all(path.exists() for path in source_paths)


def test_local_node_production_refuses_plaintext_business_stores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    config = LocalNodeConfig(
        node_id="node-one", workspace_id="business-one", base_dir=str(tmp_path / "node"),
    )

    with pytest.raises(RuntimeError, match="guardian_business_store_required"):
        configured_local_node_business_stores(config)


def test_local_node_factory_selects_guardian_when_fully_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "guardian")
    monkeypatch.setenv("TESSARIS_BUSINESS_VAULT_PATH", str(tmp_path / "vault"))
    monkeypatch.setenv("TESSARIS_BUSINESS_NAME", "Test Business")
    monkeypatch.setenv("TESSARIS_BUSINESS_STABLE_ID", "business-one")
    monkeypatch.setenv(
        "TESSARIS_BUSINESS_VAULT_KEY_B64",
        base64.urlsafe_b64encode(b"k" * 32).decode("ascii").rstrip("="),
    )
    monkeypatch.setenv("TESSARIS_APPLICATION_ROOT", str(tmp_path / "app"))
    monkeypatch.setenv("TESSARIS_UPDATE_ROOT", str(tmp_path / "updates"))
    config = LocalNodeConfig(
        node_id="node-one", workspace_id="business-one", base_dir=str(tmp_path / "node"),
    )

    queue_store, approval_store, audit_store = configured_local_node_business_stores(config)

    assert isinstance(queue_store, GuardianLocalQueueStore)
    assert isinstance(approval_store, GuardianLocalApprovalStore)
    assert isinstance(audit_store, GuardianLocalAuditStore)


def test_local_node_runtime_has_no_direct_legacy_audit_database_bypass() -> None:
    source = (
        REPOSITORY_ROOT / "backend/modules/local_node/local_node_runtime.py"
    ).read_text(encoding="utf-8")

    assert "sqlite3.connect" not in source
    assert 'Path(self.base_dir) / "audit.sqlite3"' not in source
