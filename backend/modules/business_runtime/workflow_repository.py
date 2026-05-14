from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional
import json

from .contracts_workflow import WorkflowDefinition, WorkflowRun


class WorkflowRepository:
    def __init__(self, base_dir: Path | str = ".runtime/COMDEX_MOVE/data/business_runtime") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.workflow_defs_path = self.base_dir / "workflow_definitions.json"
        self.workflow_runs_path = self.base_dir / "workflow_runs.json"

    def _load_json(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_json(self, path: Path, rows: list[dict]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        tmp.replace(path)

    def save_workflow_definition(self, wf: WorkflowDefinition) -> None:
        rows = self._load_json(self.workflow_defs_path)
        rows = [r for r in rows if r.get("id") != wf.id]
        rows.append(asdict(wf))
        self._save_json(self.workflow_defs_path, rows)

    def list_workflow_definitions(self) -> list[dict]:
        return self._load_json(self.workflow_defs_path)

    def get_workflow_definition(self, workflow_id: str) -> Optional[dict]:
        for row in self._load_json(self.workflow_defs_path):
            if row.get("id") == workflow_id:
                return row
        return None

    def save_workflow_run(self, run: WorkflowRun) -> None:
        rows = self._load_json(self.workflow_runs_path)
        rows = [r for r in rows if r.get("id") != run.id]
        rows.append(asdict(run))
        self._save_json(self.workflow_runs_path, rows)

    def get_workflow_run(self, run_id: str) -> Optional[dict]:
        for row in self._load_json(self.workflow_runs_path):
            if row.get("id") == run_id:
                return row
        return None

    def list_workflow_runs(
        self,
        department_key: str | None = None,
        operator_id: str | None = None,
        limit: int | None = 20,
    ) -> list[dict]:
        rows = self._load_json(self.workflow_runs_path)

        if department_key:
            rows = [r for r in rows if r.get("department_key") == department_key]

        if operator_id:
            rows = [r for r in rows if r.get("operator_id") == operator_id]

        rows = sorted(
            rows,
            key=lambda r: (r.get("updated_at") or r.get("created_at") or ""),
            reverse=True,
        )

        if limit is not None:
            return rows[:limit]

        return rows