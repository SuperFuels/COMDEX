from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from backend.modules.aion_business.contracts.business_containers import (
    BoardroomSnapshotContainer,
    BrandFoundationContainer,
    BusinessContainerKind,
    BusinessFinancialModelContainer,
    BusinessOperatingModelContainer,
    FinanceInboxContainer,
    OrganizationAuthorityContainer,
    BusinessIdentityContainer,
    BusinessMapContainer,
    BusinessStructureContainer,
    DepartmentIntelligenceContainer,
    OperationalRuntimeSummaryContainer,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


_CONTAINER_FILE_MAP: dict[BusinessContainerKind, str] = {
    "business_identity": "business_identity.json",
    "business_structure": "business_structure.json",
    "business_map": "business_map.json",
    "department_intelligence": "department_intelligence.json",
    "business_financial_model": "business_financial_model.json",
    "business_operating_model": "business_operating_model.json",
    "organization_authority": "organization_authority.json",
    "finance_inbox": "finance_inbox.json",
    "brand_foundation": "brand_foundation.json",
    "boardroom_snapshot": "boardroom_snapshot.json",
    "operational_runtime_summary": "operational_runtime_summary.json",
    "goal_engine_outcomes": "goal_engine_outcomes.json",
    "goal_engine_loops": "goal_engine_loops.json",
    "goal_engine_experiments": "goal_engine_experiments.json",
    "goal_engine_evidence": "goal_engine_evidence.json",
    "goal_engine_memory": "goal_engine_memory.json",
    "goal_engine_state": "goal_engine_state.json",
}


class BusinessContainerRepository:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else AIONBusinessPaths.ROOT / "business_containers"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _workspace_dir(self, workspace_id: str) -> Path:
        path = self.base_dir / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _container_path(self, workspace_id: str, kind: BusinessContainerKind) -> Path:
        return self._workspace_dir(workspace_id) / _CONTAINER_FILE_MAP[kind]

    def exists(self, workspace_id: str, kind: BusinessContainerKind) -> bool:
        return self._container_path(workspace_id, kind).exists()

    def save_model(self, model: Any) -> str:
        kind = model.kind
        path = self._container_path(model.workspace_id, kind)
        path.write_text(
            json.dumps(model.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return str(path)

    def save_dict(self, workspace_id: str, kind: BusinessContainerKind, payload: Dict[str, Any]) -> str:
        path = self._container_path(workspace_id, kind)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    def load_dict(self, workspace_id: str, kind: BusinessContainerKind) -> Dict[str, Any]:
        path = self._container_path(workspace_id, kind)
        if not path.exists():
            raise FileNotFoundError(f"Business container not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def load_optional_dict(self, workspace_id: str, kind: BusinessContainerKind) -> Optional[Dict[str, Any]]:
        if not self.exists(workspace_id, kind):
            return None
        return self.load_dict(workspace_id, kind)

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
