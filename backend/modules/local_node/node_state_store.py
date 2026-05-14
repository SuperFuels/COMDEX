from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import json
import sqlite3


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class NodeStateStore:
    """
    Persistent local node state store.

    Purpose:
    - keep current node snapshot across restarts
    - keep control flags (running / paused / stopped)
    - keep latest heartbeat payload
    - keep latest sync state payload
    - keep lightweight queue / approval counters for fast status reads

    Everything is stored as JSON in a simple key-value sqlite table so the
    runtime can evolve without constant schema churn.
    """

    def __init__(self, base_dir: str) -> None:
        self._db_path = Path(base_dir) / "node_state.sqlite3"
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
                CREATE TABLE IF NOT EXISTS node_state (
                    state_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _upsert_json(self, state_key: str, payload: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO node_state (state_key, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    state_key,
                    json.dumps(payload, ensure_ascii=False),
                    utc_now_iso(),
                ),
            )
            conn.commit()

    def _get_json(self, state_key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM node_state
                WHERE state_key = ?
                """,
                (state_key,),
            ).fetchone()

        if not row:
            return None

        try:
            data = json.loads(row["payload_json"])
        except Exception:
            return None

        return data if isinstance(data, dict) else None

    def save_node_snapshot(self, snapshot: Dict[str, Any]) -> None:
        payload = {
            **snapshot,
            "updated_at": snapshot.get("updated_at") or utc_now_iso(),
        }
        self._upsert_json("node_snapshot", payload)

    def get_node_snapshot(self) -> Dict[str, Any]:
        return self._get_json("node_snapshot") or {
            "node_id": None,
            "workspace_id": None,
            "deployment_mode": None,
            "status": "unknown",
            "updated_at": utc_now_iso(),
        }

    def save_runtime_flags(
        self,
        *,
        is_running: bool,
        is_paused: bool,
        is_stopped: bool,
        pause_reason: Optional[str] = None,
        stop_reason: Optional[str] = None,
    ) -> None:
        self._upsert_json(
            "runtime_flags",
            {
                "is_running": is_running,
                "is_paused": is_paused,
                "is_stopped": is_stopped,
                "pause_reason": pause_reason,
                "stop_reason": stop_reason,
                "updated_at": utc_now_iso(),
            },
        )

    def get_runtime_flags(self) -> Dict[str, Any]:
        return self._get_json("runtime_flags") or {
            "is_running": False,
            "is_paused": False,
            "is_stopped": True,
            "pause_reason": None,
            "stop_reason": None,
            "updated_at": utc_now_iso(),
        }

    def set_control_state(
        self,
        *,
        command: str,
        requested_by: str = "system",
        reason: Optional[str] = None,
    ) -> None:
        self._upsert_json(
            "control_state",
            {
                "command": command,
                "requested_by": requested_by,
                "reason": reason,
                "updated_at": utc_now_iso(),
            },
        )

    def get_control_state(self) -> Dict[str, Any]:
        return self._get_json("control_state") or {
            "command": "none",
            "requested_by": "system",
            "reason": None,
            "updated_at": utc_now_iso(),
        }

    def save_heartbeat(self, heartbeat: Dict[str, Any]) -> None:
        payload = {
            **heartbeat,
            "recorded_at": heartbeat.get("recorded_at") or utc_now_iso(),
        }
        self._upsert_json("heartbeat", payload)

    def get_heartbeat(self) -> Dict[str, Any]:
        return self._get_json("heartbeat") or {
            "status": "unknown",
            "recorded_at": utc_now_iso(),
        }

    def save_sync_state(self, sync_state: Dict[str, Any]) -> None:
        payload = {
            **sync_state,
            "updated_at": sync_state.get("updated_at") or utc_now_iso(),
        }
        self._upsert_json("sync_state", payload)

    def get_sync_state(self) -> Dict[str, Any]:
        return self._get_json("sync_state") or {
            "last_push_at": None,
            "last_pull_at": None,
            "last_success_at": None,
            "last_error": None,
            "pending_upload_count": 0,
            "pending_download_count": 0,
            "last_ack_token": None,
            "updated_at": utc_now_iso(),
        }

    def save_queue_metrics(
        self,
        *,
        queued_count: int,
        running_count: int,
        waiting_approval_count: int,
        completed_count: int,
        failed_count: int,
        cancelled_count: int,
    ) -> None:
        self._upsert_json(
            "queue_metrics",
            {
                "queued_count": queued_count,
                "running_count": running_count,
                "waiting_approval_count": waiting_approval_count,
                "completed_count": completed_count,
                "failed_count": failed_count,
                "cancelled_count": cancelled_count,
                "updated_at": utc_now_iso(),
            },
        )

    def get_queue_metrics(self) -> Dict[str, Any]:
        return self._get_json("queue_metrics") or {
            "queued_count": 0,
            "running_count": 0,
            "waiting_approval_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "cancelled_count": 0,
            "updated_at": utc_now_iso(),
        }

    def save_approval_metrics(
        self,
        *,
        pending_count: int,
        approved_count: int,
        rejected_count: int,
    ) -> None:
        self._upsert_json(
            "approval_metrics",
            {
                "pending_count": pending_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "updated_at": utc_now_iso(),
            },
        )

    def get_approval_metrics(self) -> Dict[str, Any]:
        return self._get_json("approval_metrics") or {
            "pending_count": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "updated_at": utc_now_iso(),
        }

    def get_full_state(self) -> Dict[str, Any]:
        return {
            "node_snapshot": self.get_node_snapshot(),
            "runtime_flags": self.get_runtime_flags(),
            "control_state": self.get_control_state(),
            "heartbeat": self.get_heartbeat(),
            "sync_state": self.get_sync_state(),
            "queue_metrics": self.get_queue_metrics(),
            "approval_metrics": self.get_approval_metrics(),
        }