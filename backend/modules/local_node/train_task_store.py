from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.local_node.contracts_local_node import utc_now_iso


class TrainTaskStore:
    def __init__(self, base_dir: str) -> None:
        self.base_path = Path(base_dir) / "train_tasks"
        self.workflow_dir = self.base_path / "workflows"
        self.run_dir = self.base_path / "runs"
        self.dedupe_path = self.base_path / "dedupe.json"

        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir.mkdir(parents=True, exist_ok=True)

        if not self.dedupe_path.exists():
            self.dedupe_path.write_text("{}", encoding="utf-8")

    def _workflow_path(self, workspace_id: str, workflow_id: str) -> Path:
        path = self.workflow_dir / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{workflow_id}.json"

    def save_workflow(
        self,
        workspace_id: str,
        workflow_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        next_payload = {
            **payload,
            "workflow_id": workflow_id,
            "workspace_id": workspace_id,
            "updated_at": now,
        }

        if not next_payload.get("created_at"):
            next_payload["created_at"] = now

        self._workflow_path(workspace_id, workflow_id).write_text(
            json.dumps(next_payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        return next_payload

    def get_workflow(
        self,
        workspace_id: str,
        workflow_id: str,
    ) -> Optional[Dict[str, Any]]:
        path = self._workflow_path(workspace_id, workflow_id)
        if not path.exists():
            return None

        return json.loads(path.read_text(encoding="utf-8"))

    def list_workflows(self, workspace_id: str) -> List[Dict[str, Any]]:
        path = self.workflow_dir / workspace_id
        if not path.exists():
            return []

        items: List[Dict[str, Any]] = []
        for file_path in sorted(path.glob("*.json")):
            try:
                items.append(json.loads(file_path.read_text(encoding="utf-8")))
            except Exception:
                continue

        return items

    def _read_dedupe(self) -> Dict[str, Any]:
        try:
            return json.loads(self.dedupe_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def has_seen(self, dedupe_key: str) -> bool:
        if not dedupe_key:
            return False
        return dedupe_key in self._read_dedupe()

    def mark_seen(self, dedupe_key: str, payload: Optional[Dict[str, Any]] = None) -> None:
        if not dedupe_key:
            return

        data = self._read_dedupe()
        data[dedupe_key] = {
            "seen_at": utc_now_iso(),
            "payload": payload or {},
        }

        self.dedupe_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def save_run(
        self,
        workspace_id: str,
        run_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        path = self.run_dir / workspace_id
        path.mkdir(parents=True, exist_ok=True)

        next_payload = {
            **payload,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "updated_at": utc_now_iso(),
        }

        (path / f"{run_id}.json").write_text(
            json.dumps(next_payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        return next_payload

    def list_runs(self, workspace_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        path = self.run_dir / workspace_id
        if not path.exists():
            return []

        items: List[Dict[str, Any]] = []
        for file_path in sorted(path.glob("*.json"), reverse=True):
            try:
                items.append(json.loads(file_path.read_text(encoding="utf-8")))
            except Exception:
                continue

        return items[:limit]