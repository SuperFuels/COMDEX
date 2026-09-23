from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional
import json
import uuid

from .contracts_approval import ApprovalRequest, ApprovalStatus
from .contracts_workflow import utc_now_iso


class ApprovalRuntime:
    def __init__(
        self,
        base_dir: Path | str = ".runtime/COMDEX_MOVE/data/business_runtime",
    ) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "approval_requests.json"

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, rows: list[dict[str, Any]]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def create_request(
        self,
        workflow_run_id: str,
        operator_id: str,
        department_key: str,
        title: str,
        summary: str,
        payload: dict[str, Any],
    ) -> ApprovalRequest:
        req = ApprovalRequest(
            id=f"approval_{uuid.uuid4().hex[:10]}",
            workflow_run_id=workflow_run_id,
            operator_id=operator_id,
            department_key=department_key,
            title=title,
            summary=summary,
            payload=payload,
        )
        rows = self._load()
        rows.append(asdict(req))
        self._save(rows)
        return req

    def get(self, approval_id: str) -> Optional[dict[str, Any]]:
        for row in self._load():
            if row.get("id") == approval_id:
                return row
        return None

    def list(
        self,
        status: str | None = None,
        department_key: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._load()

        if status:
            rows = [row for row in rows if row.get("status") == status]

        if department_key:
            rows = [row for row in rows if row.get("department_key") == department_key]

        rows = sorted(rows, key=lambda row: row.get("requested_at", ""), reverse=True)

        if limit is not None:
            rows = rows[:limit]

        return rows

    def resolve(
        self,
        approval_id: str,
        approve: bool,
        resolved_by: str,
        note: str | None = None,
    ) -> Optional[dict[str, Any]]:
        rows = self._load()
        updated: Optional[dict[str, Any]] = None

        for row in rows:
            if row.get("id") != approval_id:
                continue

            row["status"] = (
                ApprovalStatus.APPROVED.value
                if approve
                else ApprovalStatus.REJECTED.value
            )
            row["resolved_at"] = utc_now_iso()
            row["resolved_by"] = resolved_by
            row["resolution_note"] = note
            updated = row
            break

        if updated is not None:
            self._save(rows)

        return updated