from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from backend.modules.aion_agents.contracts.workflow_definition import WorkflowDefinition
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_agents.runtime.vault_repository_backend import (
    AgentVaultRepositoryBackend,
    configured_agent_domain_store,
)


class WorkflowDefinitionRepository:
    """
    File-backed repository for workflow definitions.

    Layout:
      <base_dir>/aion_agents/workflow_definitions/<workspace_id>/<workflow_id>.json
    """

    def __init__(
        self,
        base_dir: str | Path | None = None,
        *,
        domain_store: VaultDomainStore | None = None,
    ) -> None:
        self.base_dir = Path(base_dir or ".runtime")
        self.root = self.base_dir / "aion_agents" / "workflow_definitions"
        store = domain_store or (configured_agent_domain_store() if base_dir is None else None)
        self.vault = (
            AgentVaultRepositoryBackend(store, kind="workflow_definitions") if store else None
        )
        if self.vault is None:
            self.root.mkdir(parents=True, exist_ok=True)

    def _workspace_dir(self, workspace_id: str) -> Path:
        path = self.root / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _workflow_path(self, workspace_id: str, workflow_id: str) -> Path:
        return self._workspace_dir(workspace_id) / f"{workflow_id}.json"

    def save(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        workflow_id = getattr(workflow, "id", None)
        if not workflow_id:
            raise ValueError("WorkflowDefinition is missing id")

        workspace_id = getattr(workflow, "workspace_id", None)
        if not workspace_id:
            raise ValueError("WorkflowDefinition is missing workspace_id")

        if self.vault is not None:
            self.vault.put(
                workspace_id=workspace_id,
                item_id=str(workflow_id),
                payload=workflow.model_dump(mode="json"),
            )
            return workflow
        path = self._workflow_path(workspace_id, workflow_id)
        path.write_text(
            workflow.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return workflow

    def load(self, workspace_id: str, workflow_id: str) -> Optional[WorkflowDefinition]:
        if self.vault is not None:
            payload = self.vault.get(workspace_id=workspace_id, item_id=workflow_id)
            if payload is None:
                raise FileNotFoundError(
                    f"Workflow definition not found: workspace_id={workspace_id} workflow_id={workflow_id}"
                )
            return WorkflowDefinition(**payload)
        path = self._workflow_path(workspace_id, workflow_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Workflow definition not found: workspace_id={workspace_id} workflow_id={workflow_id}"
            )

        raw = path.read_text(encoding="utf-8")

        # AION O25Q empty/corrupt workflow quarantine:
        # /api/local-node/status must not crash the desktop app because a
        # workflow definition file is empty or half-written.
        if not raw.strip():
            self._quarantine_invalid_workflow_file(path, "empty")
            return None

        try:
            return WorkflowDefinition.model_validate_json(raw)
        except Exception:
            self._quarantine_invalid_workflow_file(path, "invalid_json")
            return None

    def _quarantine_invalid_workflow_file(self, path: Path, reason: str) -> None:
        try:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            target = path.with_suffix(path.suffix + f".quarantined-{reason}-{stamp}")
            path.rename(target)
            print(f"[AION O25Q] quarantined invalid workflow definition: {path} -> {target}")
        except Exception as error:
            print(f"[AION O25Q] failed to quarantine invalid workflow definition {path}: {error}")

    def get(self, workspace_id: str, workflow_id: str) -> Optional[WorkflowDefinition]:
        try:
            return self.load(workspace_id, workflow_id)
        except FileNotFoundError:
            return None

    def find_one(self, workspace_id: str, workflow_id: str) -> Optional[WorkflowDefinition]:
        return self.get(workspace_id, workflow_id)

    def exists(self, workspace_id: str, workflow_id: str) -> bool:
        if self.vault is not None:
            return self.vault.exists(workspace_id=workspace_id, item_id=workflow_id)
        return self._workflow_path(workspace_id, workflow_id).exists()

    def delete(self, workspace_id: str, workflow_id: str) -> bool:
        if self.vault is not None:
            return self.vault.delete(workspace_id=workspace_id, item_id=workflow_id)
        path = self._workflow_path(workspace_id, workflow_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_all(self, workspace_id: str) -> List[WorkflowDefinition]:
        if self.vault is not None:
            items = [WorkflowDefinition(**item) for item in self.vault.list(workspace_id=workspace_id)]
            items.sort(
                key=lambda item: getattr(item, "updated_at", None) or getattr(item, "created_at", None) or "",
                reverse=True,
            )
            return items
        directory = self._workspace_dir(workspace_id)
        items: List[WorkflowDefinition] = []

        for path in sorted(directory.glob("*.json")):
            try:
                items.append(
                    WorkflowDefinition.model_validate_json(
                        path.read_text(encoding="utf-8")
                    )
                )
            except Exception:
                continue

        items.sort(
            key=lambda item: getattr(item, "updated_at", None) or getattr(item, "created_at", None) or "",
            reverse=True,
        )
        return items

    def list_active(self, workspace_id: str) -> List[WorkflowDefinition]:
        return [
            item
            for item in self.list_all(workspace_id)
            if getattr(item, "active", True)
        ]
