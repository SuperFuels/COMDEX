from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class RoleRepository:
    def __init__(self, base_dir: Optional[str | Path] = None):
        if base_dir is not None:
            raise ValueError(
                "RoleRepository currently uses the global AIONBusinessPaths "
                "layout; base_dir override is not supported in this version."
            )

    def _role_path(self, workspace_id: str, role_id: str) -> Path:
        return AIONBusinessPaths.role_file(workspace_id, role_id)

    def save(self, role: RoleSpec) -> str:
        path = self._role_path(role.workspace_id, role.id)
        path.write_text(
            json.dumps(role.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return str(path)

    def load(self, workspace_id: str, role_id: str) -> RoleSpec:
        path = self._role_path(workspace_id, role_id)
        if not path.exists():
            raise FileNotFoundError(f"Role not found: {workspace_id}/{role_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return RoleSpec(**data)

    def list_ids(self, workspace_id: str) -> List[str]:
        path = AIONBusinessPaths.role_dir(workspace_id)
        return sorted(p.stem for p in path.glob("*.json"))

    def list_all(self, workspace_id: str) -> List[RoleSpec]:
        return [self.load(workspace_id, role_id) for role_id in self.list_ids(workspace_id)]