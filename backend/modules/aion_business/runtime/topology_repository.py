from __future__ import annotations

import json
from typing import Optional

from backend.modules.aion_business.contracts.topology import BusinessTopology
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.department_operational_store import (
    BusinessOperationsRecordRepository,
    DepartmentOperationalStore,
)


class TopologyRepository:
    """
    File-backed repository for generated business topologies.

    Storage layout:
    .runtime/AION_BUSINESS/topologies/<workspace_id>.json
    """

    def __init__(
        self, *, operational_store: DepartmentOperationalStore | None = None,
    ) -> None:
        self.records = BusinessOperationsRecordRepository(
            "topologies", operational_store=operational_store,
        )
        if not self.records.enabled:
            AIONBusinessPaths.ensure_base_dirs()

    def _path(self, workspace_id: str):
        return AIONBusinessPaths.topology_file(workspace_id)

    def save(self, topology: BusinessTopology) -> BusinessTopology:
        if self.records.enabled:
            self.records.put(
                topology.workspace_id, "topology", topology.model_dump(mode="json"),
                actor_id="topology-repository",
            )
            return topology
        path = self._path(topology.workspace_id)
        path.write_text(
            json.dumps(topology.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return topology

    def load(self, workspace_id: str) -> BusinessTopology:
        if self.records.enabled:
            record = self.records.get_optional(workspace_id, "topology")
            if record is None:
                raise FileNotFoundError(f"Topology not found: {workspace_id}")
            return BusinessTopology(**record["payload"])
        path = self._path(workspace_id)
        if not path.exists():
            raise FileNotFoundError(f"Topology not found: {workspace_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return BusinessTopology(**data)

    def load_optional(self, workspace_id: str) -> Optional[BusinessTopology]:
        if self.records.enabled:
            record = self.records.get_optional(workspace_id, "topology")
            return BusinessTopology(**record["payload"]) if record else None
        path = self._path(workspace_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return BusinessTopology(**data)

    def exists(self, workspace_id: str) -> bool:
        if self.records.enabled:
            return self.records.get_optional(workspace_id, "topology") is not None
        return self._path(workspace_id).exists()

    def delete(self, workspace_id: str) -> bool:
        if self.records.enabled:
            return self.records.delete(
                workspace_id, "topology", actor_id="topology-repository",
            )
        path = self._path(workspace_id)
        if not path.exists():
            return False
        path.unlink()
        return True
