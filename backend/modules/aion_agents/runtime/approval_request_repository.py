from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_agents.contracts.approval_request import ApprovalRequest


class ApprovalRequestRepository:
    def __init__(self, base_dir: str | Path = ".runtime") -> None:
        self.base_dir = Path(base_dir)
        self.root = self.base_dir / "aion_agents" / "approval_requests"

    def _workspace_dir(self, workspace_id: str) -> Path:
        return self.root / workspace_id

    def _path(self, workspace_id: str, approval_id: str) -> Path:
        return self._workspace_dir(workspace_id) / f"{approval_id}.json"

    def save(self, model: ApprovalRequest) -> ApprovalRequest:
        path = self._path(model.workspace_id, model.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return model

    def load(self, workspace_id: str, approval_id: str) -> ApprovalRequest:
        path = self._path(workspace_id, approval_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Approval request not found: {workspace_id}/{approval_id}"
            )
        return ApprovalRequest(**json.loads(path.read_text(encoding="utf-8")))

    def delete(self, workspace_id: str, approval_id: str) -> bool:
        path = self._path(workspace_id, approval_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_all(self, workspace_id: str) -> List[ApprovalRequest]:
        directory = self._workspace_dir(workspace_id)
        if not directory.exists():
            return []

        items: List[ApprovalRequest] = []
        for path in sorted(directory.glob("*.json")):
            try:
                items.append(ApprovalRequest(**json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue

        items.sort(key=lambda item: item.requested_at, reverse=True)
        return items

    def find_pending(self, workspace_id: str) -> List[ApprovalRequest]:
        return [item for item in self.list_all(workspace_id) if item.status == "pending"]

    def resolve(
        self,
        workspace_id: str,
        approval_id: str,
        *,
        approve: bool,
        resolved_by: str,
        resolution_note: Optional[str],
        resolved_at: str,
    ) -> Optional[ApprovalRequest]:
        item = self.find_one(workspace_id, approval_id)
        if item is None:
            return None

        item.status = "approved" if approve else "rejected"
        item.resolved_by = resolved_by
        item.resolution_note = resolution_note
        item.resolved_at = resolved_at
        return self.save(item)

    def find_one(self, workspace_id: str, approval_id: str) -> Optional[ApprovalRequest]:
        try:
            return self.load(workspace_id, approval_id)
        except FileNotFoundError:
            return None