from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import json
import sqlite3

from backend.modules.local_node.contracts_local_node import AuditEvent


class LocalAuditStore:
    def __init__(self, base_dir: str) -> None:
        self._db_path = Path(base_dir) / "audit.sqlite3"
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
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _deserialize(self, row: sqlite3.Row) -> AuditEvent:
        return AuditEvent.from_dict(json.loads(row["payload_json"]))

    def upsert(self, event: AuditEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (id, payload_json)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET payload_json=excluded.payload_json
                """,
                (event.id, json.dumps(event.to_dict(), ensure_ascii=False)),
            )
            conn.commit()

    def append(self, event: AuditEvent) -> None:
        self.upsert(event)

    def append_event(
        self,
        *,
        event_type: str,
        message: str,
        payload: Optional[dict] = None,
        level: str = "info",
        node_id: str = "node_mac_local_01",
        workspace_id: str = "costa-conexion",
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
        queue_item_id: Optional[str] = None,
        approval_id: Optional[str] = None,
    ) -> AuditEvent:
        event = AuditEvent.new(
            node_id=node_id,
            workspace_id=workspace_id,
            event_type=event_type,
            level=level,
            message=message,
            payload=payload or {},
            trace_id=trace_id,
            run_id=run_id,
            queue_item_id=queue_item_id,
            approval_id=approval_id,
        )
        self.upsert(event)
        return event

    def get(self, event_id: str) -> Optional[AuditEvent]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, payload_json FROM audit_events WHERE id = ?",
                (event_id,),
            ).fetchone()
        return self._deserialize(row) if row else None

    def list_all(self) -> List[AuditEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, payload_json FROM audit_events ORDER BY id ASC"
            ).fetchall()
        return [self._deserialize(row) for row in rows]

    def list_recent(self, limit: int = 100) -> List[AuditEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, payload_json
                FROM audit_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._deserialize(row) for row in rows]

    def tail(self, limit: int = 100) -> List[AuditEvent]:
        return self.list_recent(limit=limit)