from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.local_node.contracts_local_node import utc_now_iso


class TrainTaskApprovalStore:
    def __init__(self, base_dir: str) -> None:
        self.base_path = Path(base_dir) / "train_tasks" / "approvals"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _workspace_path(self, workspace_id: str) -> Path:
        path = self.base_path / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _approval_path(self, workspace_id: str, approval_id: str) -> Path:
        return self._workspace_path(workspace_id) / f"{approval_id}.json"

    def save_approval(
        self,
        workspace_id: str,
        approval_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        next_payload = {
            **payload,
            "approval_id": approval_id,
            "workspace_id": workspace_id,
            "updated_at": now,
        }

        if not next_payload.get("created_at"):
            next_payload["created_at"] = now

        self._approval_path(workspace_id, approval_id).write_text(
            json.dumps(next_payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        return next_payload

    def get_approval(
        self,
        workspace_id: str,
        approval_id: str,
    ) -> Optional[Dict[str, Any]]:
        path = self._approval_path(workspace_id, approval_id)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def list_approvals(
        self,
        workspace_id: str,
        *,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        path = self._workspace_path(workspace_id)
        items: List[Dict[str, Any]] = []

        for file_path in sorted(path.glob("*.json"), reverse=True):
            try:
                item = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            if status and str(item.get("status") or "") != status:
                continue

            items.append(item)

        return items[: max(1, min(int(limit or 50), 500))]
