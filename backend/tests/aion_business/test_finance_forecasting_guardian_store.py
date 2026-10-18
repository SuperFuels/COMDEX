from __future__ import annotations

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.finance_forecasting_service import FinanceForecastingService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_finance_forecast_restarts_from_encrypted_operations_domain(monkeypatch, tmp_path):
    runtime_root = tmp_path / "runtime"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", runtime_root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", runtime_root / "business_containers")
    repository = BusinessContainerRepository(runtime_root / "business_containers")
    repository.save_dict("acme", "business_financial_model", {
        "workspace_id": "acme", "kind": "business_financial_model",
        "currency": "EUR", "period_basis": "annual",
        "reporting_period": {"from": "2025-01-01", "to": "2025-12-31", "basis": "annual"},
        "metrics": {"revenue": 120000, "direct_costs": 48000, "overheads": 24000, "ending_cash": 30000},
        "evidence_refs": [], "revision": 1,
    })
    repository.save_dict("acme", "department_intelligence", {
        "workspace_id": "acme", "kind": "department_intelligence", "departments": {}, "revision": 1,
    })
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"f" * 32)
    domains = VaultDomainStore(guardian)
    service = FinanceForecastingService(repository, domain_store=domains)
    scenario, pointer = service.run(
        "acme", {"scenario_id": "private-growth", "forecast_months": 2,
                 "monthly_hiring_cost": 1234, "minimum_cash_reserve": 25000},
        scenario_name="Private growth plan", created_at="2026-10-17T12:00:00+00:00",
    )

    assert pointer["target"]["vault_entity_id"] == "scenarios/private-growth"
    restarted = FinanceForecastingService(repository, domain_store=domains)
    assert restarted.list("acme")[0]["scenario_hash"] == scenario["scenario_hash"]
    plaintext = guardian.database.read_bytes()
    assert b"Private growth plan" not in plaintext
    assert b"1234" not in plaintext
