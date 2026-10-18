from __future__ import annotations

from datetime import UTC, datetime
import sys
from typing import Any, Dict, Optional
from uuid import uuid4

from backend.modules.aion_business.contracts.business_containers import (
    BoardroomSnapshotContainer,
    BrandFoundationContainer,
    BusinessContainerKind,
    BusinessFinancialModelContainer,
    BusinessIdentityContainer,
    BusinessMapContainer,
    BusinessOperatingModelContainer,
    BusinessStructureContainer,
    DepartmentIntelligenceContainer,
    FinanceInboxContainer,
    OperationalRuntimeSummaryContainer,
    OrganizationAuthorityContainer,
)
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


CONTAINER_COLLECTION = "business_containers"
CONTAINER_VAULT_DOMAINS: dict[str, tuple[str, ...]] = {
    "business_identity": ("business.identity",),
    "business_structure": ("business.structure", "departments.map"),
    "business_map": ("business.map",),
    # Department intelligence also contains the authoritative installed and
    # founder-created department directory, so writes announce both the
    # department map and its intelligence payload.
    "department_intelligence": ("departments.map", "departments.intelligence"),
    "business_operating_model": ("departments.operational_records",),
    # People, roles and device responsibility are both security authority and
    # an operational department record.  Announcing both domains keeps the
    # discovery/release evidence aligned with the actual encrypted container.
    "organization_authority": (
        "security.records",
        "departments.operational_records",
    ),
    "brand_foundation": ("business.structure",),
    "operational_runtime_summary": ("departments.operational_records",),
}


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class GuardianBusinessContainerRepository:
    """Drop-in semantic container repository that never opens a raw business-data file."""

    def __init__(self, guardian: VaultGuardian, *, default_actor_id: str = "guardian-adapter") -> None:
        self.guardian = guardian
        self.default_actor_id = self.guardian._component(default_actor_id, "default_actor_id")

    def _record_id(self, workspace_id: str, kind: BusinessContainerKind) -> str:
        workspace = self.guardian._component(workspace_id, "workspace_id")
        container_kind = self.guardian._component(str(kind), "container_kind")
        return f"{workspace}--{container_kind}"

    @staticmethod
    def _audit_domains(kind: BusinessContainerKind, operation: str) -> None:
        for domain_id in CONTAINER_VAULT_DOMAINS.get(str(kind), ()):
            sys.audit("tessaris.vault_domain_access", domain_id, operation)

    def _read(self, workspace_id: str, kind: BusinessContainerKind) -> dict[str, Any]:
        self._audit_domains(kind, "get")
        record = self.guardian.get_record(
            collection=CONTAINER_COLLECTION,
            record_id=self._record_id(workspace_id, kind),
        )
        payload = record["payload"]
        if payload.get("workspace_id") != workspace_id or payload.get("kind") != kind:
            raise RuntimeError("guardian_container_identity_mismatch")
        return record

    def exists(self, workspace_id: str, kind: BusinessContainerKind) -> bool:
        try:
            self._read(workspace_id, kind)
        except KeyError:
            return False
        return True

    def save_model(
        self,
        model: Any,
        *,
        actor_id: str | None = None,
        idempotency_key: str | None = None,
        expected_version: int | None = None,
    ) -> str:
        return self.save_dict(
            model.workspace_id,
            model.kind,
            model.model_dump(mode="json"),
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            expected_version=expected_version,
        )

    def save_dict(
        self,
        workspace_id: str,
        kind: BusinessContainerKind,
        payload: Dict[str, Any],
        *,
        actor_id: str | None = None,
        idempotency_key: str | None = None,
        expected_version: int | None = None,
    ) -> str:
        self._audit_domains(kind, "put")
        record_id = self._record_id(workspace_id, kind)
        if expected_version is None:
            try:
                expected_version = int(self._read(workspace_id, kind)["version"])
            except KeyError:
                expected_version = None
        result = self.guardian.put_record(
            collection=CONTAINER_COLLECTION,
            record_id=record_id,
            payload={
                "schema_version": "tessaris.guardian-business-container.v1",
                "workspace_id": workspace_id,
                "kind": kind,
                "container": dict(payload),
            },
            expected_version=expected_version,
            idempotency_key=idempotency_key or f"container-{uuid4().hex}",
            actor_id=actor_id or self.default_actor_id,
            recorded_at=_now(),
        )
        return f"guardian://{CONTAINER_COLLECTION}/{record_id}?version={result['version']}"

    def load_dict(self, workspace_id: str, kind: BusinessContainerKind) -> Dict[str, Any]:
        try:
            return dict(self._read(workspace_id, kind)["payload"]["container"])
        except KeyError as exc:
            raise FileNotFoundError(
                f"business_container_not_found:{workspace_id}:{kind}"
            ) from exc

    def load_optional_dict(
        self, workspace_id: str, kind: BusinessContainerKind
    ) -> Optional[Dict[str, Any]]:
        try:
            return self.load_dict(workspace_id, kind)
        except FileNotFoundError:
            return None

    def load_business_identity(self, workspace_id: str) -> BusinessIdentityContainer:
        return BusinessIdentityContainer(**self.load_dict(workspace_id, "business_identity"))

    def load_business_structure(self, workspace_id: str) -> BusinessStructureContainer:
        return BusinessStructureContainer(**self.load_dict(workspace_id, "business_structure"))

    def load_business_map(self, workspace_id: str) -> BusinessMapContainer:
        return BusinessMapContainer(**self.load_dict(workspace_id, "business_map"))

    def load_department_intelligence(self, workspace_id: str) -> DepartmentIntelligenceContainer:
        return DepartmentIntelligenceContainer(**self.load_dict(workspace_id, "department_intelligence"))

    def load_business_financial_model(self, workspace_id: str) -> BusinessFinancialModelContainer:
        return BusinessFinancialModelContainer(**self.load_dict(workspace_id, "business_financial_model"))

    def load_business_operating_model(self, workspace_id: str) -> BusinessOperatingModelContainer:
        return BusinessOperatingModelContainer(**self.load_dict(workspace_id, "business_operating_model"))

    def load_organization_authority(self, workspace_id: str) -> OrganizationAuthorityContainer:
        return OrganizationAuthorityContainer(**self.load_dict(workspace_id, "organization_authority"))

    def load_finance_inbox(self, workspace_id: str) -> FinanceInboxContainer:
        return FinanceInboxContainer(**self.load_dict(workspace_id, "finance_inbox"))

    def load_brand_foundation(self, workspace_id: str) -> BrandFoundationContainer:
        return BrandFoundationContainer(**self.load_dict(workspace_id, "brand_foundation"))

    def load_boardroom_snapshot(self, workspace_id: str) -> BoardroomSnapshotContainer:
        return BoardroomSnapshotContainer(**self.load_dict(workspace_id, "boardroom_snapshot"))

    def load_operational_runtime_summary(self, workspace_id: str) -> OperationalRuntimeSummaryContainer:
        return OperationalRuntimeSummaryContainer(
            **self.load_dict(workspace_id, "operational_runtime_summary")
        )
