from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.business_data_domain_registry import (
    BusinessDataDomain,
    BusinessDataDomainRegistry,
    BusinessDataDomainRegistryError,
    REQUIRED_DEPARTMENT_VAULT_DOMAINS,
    department_vault_namespaces,
)


def test_core_registry_covers_named_surfaces_and_future_departments():
    registry = BusinessDataDomainRegistry()
    required_named_surfaces = {
        "business.map",
        "business.working_state",
        "departments.map",
        "departments.intelligence",
        "departments.operational_records",
        "departments.operational_audit",
        "departments.pilot_tasks",
        "departments.pilot_audit",
        "onboarding.foundation_session",
        "onboarding.receipts",
        "train_agent.automations",
        "train_agent.runs_and_audit",
        "learning.customer_state",
        "learning.audit",
        "file_cabinet.tree",
        "file_cabinet.originals",
        "file_cabinet.governance",
    }
    for domain_id in required_named_surfaces:
        assert registry.get(domain_id).contains_customer_data is True
        assert registry.get(domain_id).migration_required is True
        assert registry.get(domain_id).guardian_collection
    result = registry.release_preflight(
        feature_data_domains=[
            "business.map",
            "business.notes",
            "business.working_state",
            "business.knowledge",
            "business.knowledge_files",
            "business.knowledge_audit",
            "security.records",
            "security.audit",
            "work_schedule.records",
            "work_schedule.files",
            "support.records",
            "support.files",
            "sales.records",
            "sales.files",
            "sales.audit",
            "sales.completion_records",
            "finance.sales_records",
            "finance.bookkeeping_records",
            "finance.bookkeeping_journal",
            "finance.recurring_records",
            "finance.reconciliation_records",
            "finance.ledger_records",
            "finance.integration_records",
            "finance.operations_records",
            "finance.inbox_files",
            "departments.map",
            "departments.operational_records",
            "departments.operational_audit",
            "onboarding.foundation_session",
            "train_agent.automations",
            "learning.customer_state",
            "learning.audit",
            "file_cabinet.tree",
            "file_cabinet.originals",
        ],
        department_ids=["finance", "sales", "new-department-from-update"],
    )
    assert result["approved"] is True
    assert result["future_department_policy"] == "covered_by_guardian_wildcard"


def test_release_preflight_rejects_new_customer_data_feature_until_registered():
    registry = BusinessDataDomainRegistry()
    with pytest.raises(BusinessDataDomainRegistryError, match="undeclared.feature"):
        registry.release_preflight(
            feature_data_domains=["undeclared.feature"], department_ids=[]
        )

    registry.register(
        BusinessDataDomain(
            "undeclared.feature", "authoritative_record", "feature_records"
        )
    )
    assert registry.release_preflight(
        feature_data_domains=["undeclared.feature"], department_ids=[]
    )["approved"] is True


def test_customer_data_domain_cannot_opt_out_of_migration():
    with pytest.raises(BusinessDataDomainRegistryError, match="migration_contract_required"):
        BusinessDataDomainRegistry(
            [
                BusinessDataDomain(
                    "unsafe.feature",
                    "authoritative_record",
                    "unsafe",
                    migration_required=False,
                )
            ]
        )


def test_future_department_contract_has_isolated_namespaces_for_every_surface():
    namespaces = department_vault_namespaces("new_department_from_update")
    assert set(namespaces) == set(REQUIRED_DEPARTMENT_VAULT_DOMAINS)
    assert all(
        value.startswith("departments/new_department_from_update/")
        for value in namespaces.values()
    )
    assert len(set(namespaces.values())) == len(REQUIRED_DEPARTMENT_VAULT_DOMAINS)


def test_future_department_identity_cannot_escape_vault_namespace():
    with pytest.raises(BusinessDataDomainRegistryError, match="department_identity_invalid"):
        department_vault_namespaces("../other-business")
