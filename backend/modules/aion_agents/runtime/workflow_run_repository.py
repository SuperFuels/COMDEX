from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_agents.contracts.workflow_run import WorkflowRun
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_agents.runtime.vault_repository_backend import (
    AgentVaultRepositoryBackend,
    configured_agent_domain_store,
)


class WorkflowRunRepository:
    def __init__(
        self,
        base_dir: str | Path | None = None,
        *,
        domain_store: VaultDomainStore | None = None,
    ) -> None:
        self.base_dir = Path(base_dir or ".runtime")
        self.root = self.base_dir / "aion_agents" / "workflow_runs"
        store = domain_store or (configured_agent_domain_store() if base_dir is None else None)
        self.vault = AgentVaultRepositoryBackend(
            store, kind="workflow_runs", audit=True
        ) if store else None

    def _workspace_dir(self, workspace_id: str) -> Path:
        return self.root / workspace_id

    def _path(self, workspace_id: str, run_id: str) -> Path:
        return self._workspace_dir(workspace_id) / f"{run_id}.json"

    def save(self, model: WorkflowRun) -> WorkflowRun:
        if self.vault is not None:
            self.vault.put(
                workspace_id=model.workspace_id,
                item_id=model.id,
                payload=model.model_dump(mode="json"),
            )
            return model
        path = self._path(model.workspace_id, model.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return model

    def load(self, workspace_id: str, run_id: str) -> WorkflowRun:
        if self.vault is not None:
            payload = self.vault.get(workspace_id=workspace_id, item_id=run_id)
            if payload is None:
                raise FileNotFoundError(f"Workflow run not found: {workspace_id}/{run_id}")
            return WorkflowRun(**payload)
        path = self._path(workspace_id, run_id)
        if not path.exists():
            raise FileNotFoundError(f"Workflow run not found: {workspace_id}/{run_id}")
        return WorkflowRun(**json.loads(path.read_text(encoding="utf-8")))

    def delete(self, workspace_id: str, run_id: str) -> bool:
        if self.vault is not None:
            return self.vault.delete(workspace_id=workspace_id, item_id=run_id)
        path = self._path(workspace_id, run_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_all(self, workspace_id: str) -> List[WorkflowRun]:
        if self.vault is not None:
            items = [WorkflowRun(**item) for item in self.vault.list(workspace_id=workspace_id)]
            items.sort(key=lambda item: item.updated_at, reverse=True)
            return items
        directory = self._workspace_dir(workspace_id)
        if not directory.exists():
            return []

        items: List[WorkflowRun] = []
        for path in sorted(directory.glob("*.json")):
            try:
                items.append(WorkflowRun(**json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue

        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    def find_by_status(
        self,
        workspace_id: str,
        status: str,
    ) -> List[WorkflowRun]:
        return [item for item in self.list_all(workspace_id) if item.status == status]

    def find_one(self, workspace_id: str, run_id: str) -> Optional[WorkflowRun]:
        try:
            return self.load(workspace_id, run_id)
        except FileNotFoundError:
            return None
