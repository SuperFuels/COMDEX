from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Literal, Mapping


StorageClass = Literal[
    "authoritative_record",
    "original_file",
    "append_only_evidence",
    "derived_rebuildable",
    "portable_export",
]


@dataclass(frozen=True)
class BusinessDataDomain:
    domain_id: str
    storage_class: StorageClass
    guardian_collection: str
    contains_customer_data: bool = True
    department_scope: str = "business"
    migration_required: bool = True


REQUIRED_DEPARTMENT_VAULT_DOMAINS: frozenset[str] = frozenset(
    {
        "departments.map",
        "departments.intelligence",
        "departments.operational_records",
        "departments.operational_audit",
        "departments.pilot_tasks",
        "departments.pilot_audit",
        "train_agent.automations",
        "train_agent.runs_and_audit",
        "file_cabinet.tree",
        "file_cabinet.originals",
        "file_cabinet.governance",
    }
)


PROTECTED_CONTINUITY_SURFACE_DOMAINS: Mapping[str, frozenset[str]] = {
    "business_and_department_maps": frozenset(
        {
            "business.map",
            "business.map_governance",
            "departments.map",
            "departments.intelligence",
        }
    ),
    "onboarding_and_pilot": frozenset(
        {
            "business.working_state",
            "onboarding.foundation_session",
            "onboarding.receipts",
            "departments.pilot_tasks",
            "departments.pilot_audit",
        }
    ),
    "train_agent": frozenset(
        {
            "business.working_state",
            "train_agent.automations",
            "train_agent.runs_and_audit",
        }
    ),
    "whole_file_cabinet": frozenset(
        {
            "file_cabinet.tree",
            "file_cabinet.originals",
            "file_cabinet.governance",
        }
    ),
}


_DEPARTMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def department_vault_namespaces(department_id: str) -> Mapping[str, str]:
    """Return the mandatory customer-owned namespace plan for one department.

    The paths are logical Guardian namespaces, not application filesystem paths.
    Keeping the department identity in every namespace prevents a later release
    from accidentally placing one department's records beneath another.
    """

    department_id = str(department_id or "").strip()
    if not _DEPARTMENT_ID.fullmatch(department_id):
        raise BusinessDataDomainRegistryError(
            f"department_identity_invalid:{department_id}"
        )
    prefix = f"departments/{department_id}"
    return {
        domain_id: f"{prefix}/{domain_id.replace('.', '/')}"
        for domain_id in sorted(REQUIRED_DEPARTMENT_VAULT_DOMAINS)
    }


CORE_BUSINESS_DATA_DOMAINS: tuple[BusinessDataDomain, ...] = (
    BusinessDataDomain("business.identity", "authoritative_record", "business_containers"),
    BusinessDataDomain("business.structure", "authoritative_record", "business_containers"),
    BusinessDataDomain("business.map", "authoritative_record", "business_containers"),
    BusinessDataDomain("business.map_governance", "append_only_evidence", "business_map_governance"),
    BusinessDataDomain("business.notes", "authoritative_record", "founder_notes"),
    BusinessDataDomain("business.working_state", "authoritative_record", "business_working_state"),
    BusinessDataDomain(
        "provider.model_selections",
        "authoritative_record",
        "provider_model_selections",
    ),
    BusinessDataDomain("business.knowledge", "authoritative_record", "business_knowledge", department_scope="all_current_and_future_departments"),
    BusinessDataDomain("business.knowledge_files", "original_file", "original_files", department_scope="all_current_and_future_departments"),
    BusinessDataDomain("business.knowledge_audit", "append_only_evidence", "business_knowledge_audit", department_scope="all_current_and_future_departments"),
    BusinessDataDomain("security.records", "authoritative_record", "security_records", department_scope="all_current_and_future_departments"),
    BusinessDataDomain("security.audit", "append_only_evidence", "security_audit", department_scope="all_current_and_future_departments"),
    BusinessDataDomain("work_schedule.records", "authoritative_record", "work_schedule_records"),
    BusinessDataDomain("work_schedule.files", "original_file", "original_files"),
    BusinessDataDomain("support.records", "authoritative_record", "support_records", department_scope="all_current_and_future_departments"),
    BusinessDataDomain("support.files", "original_file", "original_files", department_scope="all_current_and_future_departments"),
    BusinessDataDomain("sales.records", "authoritative_record", "sales_records", department_scope="all_current_and_future_departments"),
    BusinessDataDomain("sales.files", "original_file", "original_files", department_scope="all_current_and_future_departments"),
    BusinessDataDomain("sales.audit", "append_only_evidence", "sales_audit", department_scope="all_current_and_future_departments"),
    BusinessDataDomain(
        "sales.completion_records",
        "authoritative_record",
        "sales_completion_records",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "finance.sales_records",
        "authoritative_record",
        "finance_sales_records",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "finance.bookkeeping_records",
        "authoritative_record",
        "finance_bookkeeping_records",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "finance.bookkeeping_journal",
        "append_only_evidence",
        "finance_bookkeeping_journal",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "finance.recurring_records",
        "authoritative_record",
        "finance_recurring_records",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "finance.reconciliation_records",
        "authoritative_record",
        "finance_reconciliation_records",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "finance.ledger_records",
        "derived_rebuildable",
        "finance_ledger_records",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "finance.integration_records",
        "authoritative_record",
        "finance_integration_records",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "finance.operations_records",
        "authoritative_record",
        "finance_operations_records",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "finance.inbox_files",
        "original_file",
        "original_files",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "departments.map",
        "authoritative_record",
        "business_containers",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "departments.intelligence",
        "authoritative_record",
        "business_containers",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "departments.operational_records",
        "authoritative_record",
        "department_operational_records",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "departments.operational_audit",
        "append_only_evidence",
        "department_operational_audit",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "departments.pilot_tasks",
        "authoritative_record",
        "department_pilot_tasks",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "departments.pilot_audit",
        "append_only_evidence",
        "department_pilot_audit",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain("onboarding.foundation_session", "authoritative_record", "foundation_onboarding"),
    BusinessDataDomain("onboarding.receipts", "append_only_evidence", "foundation_onboarding_receipts"),
    BusinessDataDomain(
        "train_agent.automations",
        "authoritative_record",
        "pilot_operating_team",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "train_agent.runs_and_audit",
        "append_only_evidence",
        "pilot_operating_team_audit",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "learning.customer_state",
        "authoritative_record",
        "customer_learning_state",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain(
        "learning.audit",
        "append_only_evidence",
        "customer_learning_audit",
        department_scope="all_current_and_future_departments",
    ),
    BusinessDataDomain("file_cabinet.tree", "authoritative_record", "workflow_file_cabinet"),
    BusinessDataDomain("file_cabinet.originals", "original_file", "original_files"),
    BusinessDataDomain("file_cabinet.governance", "append_only_evidence", "file_cabinet_receipts"),
    BusinessDataDomain("vault.migration_receipts", "append_only_evidence", "migration_receipts"),
)


class BusinessDataDomainRegistryError(ValueError):
    pass


class BusinessDataDomainRegistry:
    """Release gate for every present and future customer-data surface.

    A department added by an update is covered by the explicit wildcard
    department domains.  A genuinely new feature/data shape must declare a
    domain before release and must name a Guardian collection and migration.
    """

    def __init__(self, domains: Iterable[BusinessDataDomain] = CORE_BUSINESS_DATA_DOMAINS) -> None:
        self._domains: dict[str, BusinessDataDomain] = {}
        for domain in domains:
            self.register(domain)

    def register(self, domain: BusinessDataDomain) -> None:
        key = str(domain.domain_id or "").strip()
        if not key or key in self._domains:
            raise BusinessDataDomainRegistryError(f"business_data_domain_invalid_or_duplicate:{key}")
        if domain.contains_customer_data and not domain.guardian_collection:
            raise BusinessDataDomainRegistryError(f"guardian_collection_required:{key}")
        if domain.contains_customer_data and not domain.migration_required:
            raise BusinessDataDomainRegistryError(f"migration_contract_required:{key}")
        self._domains[key] = domain

    def get(self, domain_id: str) -> BusinessDataDomain:
        try:
            return self._domains[domain_id]
        except KeyError as exc:
            raise BusinessDataDomainRegistryError(
                f"undeclared_business_data_domain:{domain_id}"
            ) from exc

    def release_preflight(
        self,
        *,
        feature_data_domains: Iterable[str],
        department_ids: Iterable[str],
        require_complete_registry: bool = False,
    ) -> dict[str, object]:
        requested = sorted({str(value).strip() for value in feature_data_domains if str(value).strip()})
        missing = [domain_id for domain_id in requested if domain_id not in self._domains]
        wildcard = any(
            domain.department_scope == "all_current_and_future_departments"
            for domain in self._domains.values()
        )
        departments = sorted({str(value).strip() for value in department_ids if str(value).strip()})
        if departments and not wildcard:
            missing.append("departments.*")
        omitted_registered = sorted(set(self._domains) - set(requested))
        if require_complete_registry and omitted_registered:
            missing.extend(f"release_omits:{domain_id}" for domain_id in omitted_registered)
        if missing:
            raise BusinessDataDomainRegistryError(
                "vault_release_preflight_failed:" + ",".join(sorted(set(missing)))
            )
        return {
            "schema_version": "tessaris.business-data-domain-release-preflight.v1",
            "approved": True,
            "declared_domain_count": len(self._domains),
            "feature_data_domains": requested,
            "department_ids": departments,
            "future_department_policy": "covered_by_guardian_wildcard",
            "new_feature_policy": "explicit_domain_and_migration_required",
            "complete_registry_required": require_complete_registry,
        }

    def manifest(self) -> Mapping[str, BusinessDataDomain]:
        return dict(self._domains)
