from __future__ import annotations

import json
from pathlib import Path
from typing import List

from backend.modules.aion_business.contracts.workspace import WorkspaceSpec


class WorkspaceRepository:
    def __init__(self, base_dir: str | Path = ".runtime/AION_BUSINESS/workspaces"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _workspace_path(self, workspace_id: str) -> Path:
        return self.base_dir / f"{workspace_id}.json"

    def save(self, workspace: WorkspaceSpec) -> str:
        path = self._workspace_path(workspace.id)
        path.write_text(
            json.dumps(workspace.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return str(path)

    def load(self, workspace_id: str) -> WorkspaceSpec:
        path = self._workspace_path(workspace_id)
        if not path.exists():
            raise FileNotFoundError(f"Workspace not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return WorkspaceSpec(**data)

    def list_ids(self) -> List[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))

    def register_container_binding(self, workspace_id: str, binding_id: str) -> WorkspaceSpec:
        ws = self.load(workspace_id)
        if binding_id not in ws.container_binding_ids:
            ws.container_binding_ids.append(binding_id)
            self.save(ws)
        return ws