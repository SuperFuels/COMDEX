from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from backend.modules.local_node.contracts_local_node import (
    QueueItem,
    QueueItemStatus,
    utc_now_iso,
)


class LocalQueueStore:
    def __init__(self, base_dir: str) -> None:
        self._db_path = Path(base_dir) / "queue.sqlite3"
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
                CREATE TABLE IF NOT EXISTS queue_items (
                    id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert(self, item: QueueItem) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO queue_items (id, payload_json)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET payload_json = excluded.payload_json
                """,
                (
                    item.id,
                    json.dumps(item.to_dict(), ensure_ascii=False),
                ),
            )
            conn.commit()

    def _deserialize(self, row: sqlite3.Row) -> QueueItem:
        data = json.loads(row["payload_json"])
        return QueueItem.from_dict(data)

    def list_all(self) -> List[QueueItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, payload_json FROM queue_items"
            ).fetchall()
        return [self._deserialize(row) for row in rows]

    def list_by_status(self, status: str) -> List[QueueItem]:
        return [item for item in self.list_all() if item.status == status]

    def get(self, item_id: str) -> Optional[QueueItem]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, payload_json FROM queue_items WHERE id = ?",
                (item_id,),
            ).fetchone()
        return self._deserialize(row) if row else None

    def enqueue(self, item: QueueItem) -> None:
        self.upsert(item)

    def get_next_queued(self) -> Optional[QueueItem]:
        queued = sorted(
            self.list_by_status(QueueItemStatus.QUEUED.value),
            key=lambda x: x.created_at,
        )
        return queued[0] if queued else None

    def mark_running(self, item_id: str, *, run_id: str) -> Optional[QueueItem]:
        item = self.get(item_id)
        if not item:
            return None
        item.status = QueueItemStatus.RUNNING.value
        item.run_id = run_id
        item.started_at = utc_now_iso()
        item.updated_at = utc_now_iso()
        self.upsert(item)
        return item

    def mark_waiting_approval(self, item_id: str) -> Optional[QueueItem]:
        item = self.get(item_id)
        if not item:
            return None
        item.status = QueueItemStatus.WAITING_APPROVAL.value
        item.updated_at = utc_now_iso()
        self.upsert(item)
        return item

    def mark_completed(self, item_id: str) -> Optional[QueueItem]:
        item = self.get(item_id)
        if not item:
            return None
        item.status = QueueItemStatus.COMPLETED.value
        item.completed_at = utc_now_iso()
        item.updated_at = utc_now_iso()
        self.upsert(item)
        return item

    def mark_failed(self, item_id: str, reason: str) -> Optional[QueueItem]:
        item = self.get(item_id)
        if not item:
            return None
        item.status = QueueItemStatus.FAILED.value
        item.failure_reason = reason
        item.completed_at = utc_now_iso()
        item.updated_at = utc_now_iso()
        self.upsert(item)
        return item

    def mark_cancelled(self, item_id: str, reason: str = "cancelled") -> Optional[QueueItem]:
        item = self.get(item_id)
        if not item:
            return None
        item.status = QueueItemStatus.CANCELLED.value
        item.failure_reason = reason
        item.completed_at = utc_now_iso()
        item.updated_at = utc_now_iso()
        self.upsert(item)
        return item

    def count_running(self) -> int:
        return len(self.list_by_status(QueueItemStatus.RUNNING.value))

    def count_pending(self) -> int:
        return len(self.list_by_status(QueueItemStatus.QUEUED.value))