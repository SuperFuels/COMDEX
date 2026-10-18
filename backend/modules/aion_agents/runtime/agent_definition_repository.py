from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_agents.contracts.agent_definition import AgentDefinition
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_agents.runtime.vault_repository_backend import (
    AgentVaultRepositoryBackend,
    configured_agent_domain_store,
)


class AgentDefinitionRepository:
    """
    File-backed repository for agent definitions.

    Canonical layout:
      <base_dir>/<workspace_id>/aion_agents/agent_definitions/<agent_id>.json
    """

    def __init__(
        self,
        base_dir: str | Path | None = None,
        *,
        domain_store: VaultDomainStore | None = None,
    ) -> None:
        self.base_dir = Path(base_dir or ".runtime")
        store = domain_store or (configured_agent_domain_store() if base_dir is None else None)
        self.vault = (
            AgentVaultRepositoryBackend(store, kind="agent_definitions") if store else None
        )

    def _workspace_dir(self, workspace_id: str) -> Path:
        return self.base_dir / workspace_id / "aion_agents" / "agent_definitions"

    def _path(self, workspace_id: str, agent_id: str) -> Path:
        return self._workspace_dir(workspace_id) / f"{agent_id}.json"

    def save(self, model: AgentDefinition) -> AgentDefinition:
        agent_id = getattr(model, "id", None) or getattr(model, "agent_id", None)
        if not agent_id:
            raise ValueError("AgentDefinition missing id/agent_id")

        if self.vault is not None:
            self.vault.put(
                workspace_id=model.workspace_id,
                item_id=str(agent_id),
                payload=model.model_dump(mode="json"),
            )
            return model
        path = self._path(model.workspace_id, str(agent_id))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return model

    def load(self, workspace_id: str, agent_id: str) -> AgentDefinition:
        if self.vault is not None:
            payload = self.vault.get(workspace_id=workspace_id, item_id=agent_id)
            if payload is None:
                raise FileNotFoundError(
                    f"Agent definition not found: workspace_id={workspace_id} agent_id={agent_id}"
                )
            return AgentDefinition(**payload)
        path = self._path(workspace_id, agent_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Agent definition not found: workspace_id={workspace_id} agent_id={agent_id}"
            )
        return AgentDefinition(**json.loads(path.read_text(encoding="utf-8")))

    def get(self, workspace_id: str, agent_id: str) -> Optional[AgentDefinition]:
        try:
            return self.load(workspace_id, agent_id)
        except FileNotFoundError:
            return None

    def find_one(self, workspace_id: str, agent_id: str) -> Optional[AgentDefinition]:
        return self.get(workspace_id, agent_id)

    def exists(self, workspace_id: str, agent_id: str) -> bool:
        if self.vault is not None:
            return self.vault.exists(workspace_id=workspace_id, item_id=agent_id)
        return self._path(workspace_id, agent_id).exists()

    def delete(self, workspace_id: str, agent_id: str) -> bool:
        if self.vault is not None:
            return self.vault.delete(workspace_id=workspace_id, item_id=agent_id)
        path = self._path(workspace_id, agent_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_all(self, workspace_id: str) -> List[AgentDefinition]:
        if self.vault is not None:
            items = [AgentDefinition(**item) for item in self.vault.list(workspace_id=workspace_id)]
            items.sort(
                key=lambda item: getattr(item, "updated_at", "") or "",
                reverse=True,
            )
            return items
        directory = self._workspace_dir(workspace_id)
        if not directory.exists():
            return []

        items: List[AgentDefinition] = []
        for path in sorted(directory.glob("*.json")):
            try:
                items.append(
                    AgentDefinition(**json.loads(path.read_text(encoding="utf-8")))
                )
            except Exception:
                continue

        items.sort(
            key=lambda item: getattr(item, "updated_at", "") or "",
            reverse=True,
        )
        return items
