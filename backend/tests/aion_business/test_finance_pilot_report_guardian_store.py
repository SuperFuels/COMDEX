from __future__ import annotations

from types import SimpleNamespace

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.department_pilot_repository import DepartmentPilotRepository
from backend.modules.aion_business.runtime.finance_pilot_execution_service import FinancePilotExecutionService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_finance_pilot_report_restarts_from_encrypted_operations_domain(monkeypatch, tmp_path):
    runtime_root = tmp_path / "runtime"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", runtime_root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", runtime_root / "business_containers")
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"r" * 32)
    domains = VaultDomainStore(guardian)
    service = FinancePilotExecutionService(
        task_repository=DepartmentPilotRepository(tmp_path / "tasks"),
        container_repository=BusinessContainerRepository(runtime_root / "business_containers"),
        domain_store=domains,
    )
    envelope = SimpleNamespace(
        task=SimpleNamespace(workspace_id="acme", task_id="task-private", title="Private review"),
        package=SimpleNamespace(boardroom_session_id="session-private", package_id="package-private"),
        envelope_hash="hash-private", retrieved_evidence=[], artifacts=[],
    )
    report = {
        "report_id": "finance-report-private", "workspace_id": "acme",
        "executive_summary": "Private customer management report", "metrics": {"cash": 12345},
    }
    artifact, pointer = service._store_report(
        envelope, report, "2026-10-17T12:00:00+00:00", "finance-pilot",
    )
    envelope.artifacts = [artifact]

    restarted = FinancePilotExecutionService(
        task_repository=service.task_repository,
        container_repository=service.container_repository,
        domain_store=domains,
    )
    assert restarted._load_report(envelope)["metrics"]["cash"] == 12345
    assert pointer["target"]["vault_entity_id"] == "reports/finance-report-private"
    plaintext = guardian.database.read_bytes()
    assert b"Private customer management report" not in plaintext
    assert b"12345" not in plaintext
