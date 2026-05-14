from __future__ import annotations

import json
from pathlib import Path
from typing import List

from backend.modules.aion_business.contracts.external_work_orders import (
    ExternalWorkOrderRecord,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class ExternalWorkOrderRepository:
    def _path(self, workspace_id: str, work_order_id: str) -> Path:
        return AIONBusinessPaths.external_work_order_file(workspace_id, work_order_id)

    def save(self, record: ExternalWorkOrderRecord) -> Path:
        path = self._path(record.workspace_id, record.id)
        path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, workspace_id: str, work_order_id: str) -> ExternalWorkOrderRecord:
        path = self._path(workspace_id, work_order_id)
        if not path.exists():
            raise FileNotFoundError(f"External work order not found: {workspace_id}/{work_order_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ExternalWorkOrderRecord(**data)

    def list_ids(self, workspace_id: str) -> List[str]:
        path = AIONBusinessPaths.external_work_order_dir(workspace_id)
        return sorted(p.stem for p in path.glob("*.json"))

    def list_all(self, workspace_id: str) -> List[ExternalWorkOrderRecord]:
        return [self.load(workspace_id, work_order_id) for work_order_id in self.list_ids(workspace_id)]