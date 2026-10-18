from __future__ import annotations

import json
from pathlib import Path
from typing import List

from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.department_operational_store import (
    BusinessOperationsRecordRepository,
    DepartmentOperationalStore,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class WorkspaceRepository:
    def __init__(
        self, base_dir: str | Path | None = None, *,
        operational_store: DepartmentOperationalStore | None = None,
    ):
        self.records = BusinessOperationsRecordRepository(
            "workspaces", operational_store=operational_store,
        )
        self.base_dir = Path(base_dir) if base_dir is not None else AIONBusinessPaths.WORKSPACES
        if base_dir is not None or not self.records.enabled:
            self.base_dir.mkdir(parents=True, exist_ok=True)

    def _workspace_path(self, workspace_id: str) -> Path:
        return self.base_dir / f"{workspace_id}.json"

    def save(self, workspace: WorkspaceSpec) -> str:
        if self.records.enabled and self.base_dir == AIONBusinessPaths.WORKSPACES:
            self.records.put(
                workspace.id, "workspace", workspace.model_dump(mode="json"),
                actor_id="workspace-repository",
            )
            return f"vault://departments.operational_records/{workspace.id}/business_operations/workspaces/workspace"
        path = self._workspace_path(workspace.id)
        path.write_text(
            json.dumps(workspace.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return str(path)

    def load(self, workspace_id: str) -> WorkspaceSpec:
        if self.records.enabled and self.base_dir == AIONBusinessPaths.WORKSPACES:
            record = self.records.get_optional(workspace_id, "workspace")
            if record is None:
                raise FileNotFoundError(f"Workspace not found: {workspace_id}")
            return WorkspaceSpec(**record["payload"])
        path = self._workspace_path(workspace_id)
        if not path.exists():
            raise FileNotFoundError(f"Workspace not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return WorkspaceSpec(**data)

    def list_ids(self) -> List[str]:
        if self.records.enabled and self.base_dir == AIONBusinessPaths.WORKSPACES:
            return sorted(str(row["workspace_id"]) for row in self.records.list_all())
        return sorted(p.stem for p in self.base_dir.glob("*.json"))

    def register_container_binding(self, workspace_id: str, binding_id: str) -> WorkspaceSpec:
        ws = self.load(workspace_id)
        if binding_id not in ws.container_binding_ids:
            ws.container_binding_ids.append(binding_id)
            self.save(ws)
        return ws
