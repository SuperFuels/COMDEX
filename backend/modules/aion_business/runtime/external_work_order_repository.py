from __future__ import annotations

import json
from pathlib import Path
from typing import List

from backend.modules.aion_business.contracts.external_work_orders import (
    ExternalWorkOrderRecord,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.department_operational_store import (
    DepartmentOperationalStore,
)


class ExternalWorkOrderRepository:
    def __init__(
        self, *, operational_store: DepartmentOperationalStore | None = None,
    ) -> None:
        self.operational_store = operational_store or DepartmentOperationalStore()

    def _path(self, workspace_id: str, work_order_id: str) -> Path:
        return AIONBusinessPaths.external_work_order_file(workspace_id, work_order_id)

    def save(self, record: ExternalWorkOrderRecord) -> Path | str:
        if self.operational_store.domain_store is not None:
            self.operational_store.put(
                workspace_id=record.workspace_id,
                department_id="business_operations",
                feature_id="external_work_orders",
                record_id=record.id,
                payload=record.model_dump(mode="json"),
                actor_id="external-work-order-runtime",
            )
            return f"vault://departments.operational_records/{record.workspace_id}/business_operations/external_work_orders/{record.id}"
        path = self._path(record.workspace_id, record.id)
        path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, workspace_id: str, work_order_id: str) -> ExternalWorkOrderRecord:
        if self.operational_store.domain_store is not None:
            record = self.operational_store.get_optional(
                workspace_id=workspace_id,
                department_id="business_operations",
                feature_id="external_work_orders",
                record_id=work_order_id,
            )
            if record is None:
                raise FileNotFoundError(f"External work order not found: {workspace_id}/{work_order_id}")
            return ExternalWorkOrderRecord(**record["payload"])
        path = self._path(workspace_id, work_order_id)
        if not path.exists():
            raise FileNotFoundError(f"External work order not found: {workspace_id}/{work_order_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ExternalWorkOrderRecord(**data)

    def list_ids(self, workspace_id: str) -> List[str]:
        if self.operational_store.domain_store is not None:
            return sorted(
                ExternalWorkOrderRecord(**row["payload"]).id
                for row in self.operational_store.list_feature(
                    workspace_id=workspace_id,
                    department_id="business_operations",
                    feature_id="external_work_orders",
                )
            )
        path = AIONBusinessPaths.external_work_order_dir(workspace_id)
        return sorted(p.stem for p in path.glob("*.json"))

    def list_all(self, workspace_id: str) -> List[ExternalWorkOrderRecord]:
        return [self.load(workspace_id, work_order_id) for work_order_id in self.list_ids(workspace_id)]
