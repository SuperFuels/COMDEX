from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import json
import sqlite3

from backend.modules.local_node.contracts_local_node import (
    ApprovalRecord,
    ApprovalStatus,
    utc_now_iso,
)


class LocalApprovalStore:
    def __init__(self, base_dir: str) -> None:
        self._db_path = Path(base_dir) / "approvals.sqlite3"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _deserialize(self, row: sqlite3.Row) -> ApprovalRecord:
        return ApprovalRecord.from_dict(json.loads(row["payload_json"]))

    def upsert(self, approval: ApprovalRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO approvals (id, payload_json)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET payload_json=excluded.payload_json
                """,
                (approval.id, json.dumps(approval.to_dict(), ensure_ascii=False)),
            )
            conn.commit()

    def get(self, approval_id: str) -> Optional[ApprovalRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, payload_json FROM approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
        return self._deserialize(row) if row else None

    def list_all(self) -> List[ApprovalRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, payload_json FROM approvals ORDER BY id ASC"
            ).fetchall()
        return [self._deserialize(row) for row in rows]

    def list_pending(self) -> List[ApprovalRecord]:
        return [a for a in self.list_all() if a.status == ApprovalStatus.PENDING.value]

    def resolve(
        self,
        approval_id: str,
        *,
        approve: bool,
        resolved_by: str,
        resolution_note: Optional[str] = None,
    ) -> Optional[ApprovalRecord]:
        approval = self.get(approval_id)
        if not approval:
            return None

        approval.status = (
            ApprovalStatus.APPROVED.value if approve else ApprovalStatus.REJECTED.value
        )
        approval.resolved_at = utc_now_iso()
        approval.resolved_by = resolved_by
        approval.resolution_note = resolution_note
        self.upsert(approval)
        return approval

    def link_queue_item(
        self,
        *,
        approval_request_id: str,
        queue_item_id: str,
        run_id: Optional[str] = None,
    ) -> Optional[ApprovalRecord]:
        approval = self.get(approval_request_id)
        if not approval:
            return None

        approval.queue_item_id = queue_item_id
        if run_id:
            approval.run_id = run_id
        self.upsert(approval)
        return approval