from __future__ import annotations

import json
from typing import Optional

from backend.modules.aion_business.contracts.topology import BusinessTopology
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class TopologyRepository:
    """
    File-backed repository for generated business topologies.

    Storage layout:
    .runtime/AION_BUSINESS/topologies/<workspace_id>.json
    """

    def __init__(self) -> None:
        AIONBusinessPaths.ensure_base_dirs()

    def _path(self, workspace_id: str):
        return AIONBusinessPaths.topology_file(workspace_id)

    def save(self, topology: BusinessTopology) -> BusinessTopology:
        path = self._path(topology.workspace_id)
        path.write_text(
            json.dumps(topology.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return topology

    def load(self, workspace_id: str) -> BusinessTopology:
        path = self._path(workspace_id)
        if not path.exists():
            raise FileNotFoundError(f"Topology not found: {workspace_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return BusinessTopology(**data)

    def load_optional(self, workspace_id: str) -> Optional[BusinessTopology]:
        path = self._path(workspace_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return BusinessTopology(**data)

    def exists(self, workspace_id: str) -> bool:
        return self._path(workspace_id).exists()

    def delete(self, workspace_id: str) -> bool:
        path = self._path(workspace_id)
        if not path.exists():
            return False
        path.unlink()
        return True