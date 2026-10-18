from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json
import sqlite3

from backend.modules.local_node.contracts_local_node import utc_now_iso
from backend.modules.local_node.private_sqlite import connect_private_sqlite
from backend.modules.local_node.content_free_state import (
    safe_error_code,
    safe_fingerprint,
    safe_timestamp,
)


_ALLOWED_CURSOR_KEYS = {
    "cloud_push",
    "cloud_pull",
    "cloud_ack",
    "cloud_success",
    "cloud_error",
}


class SyncCursorStore:
    def __init__(self, base_dir: str) -> None:
        self._db_path = Path(base_dir) / "sync_cursor.sqlite3"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._scrub_legacy_content()

    def _connect(self) -> sqlite3.Connection:
        return connect_private_sqlite(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_cursors (
                    cursor_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _sanitize_payload(self, cursor_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if cursor_key == "cloud_push":
            return {"last_push_at": safe_timestamp(payload.get("last_push_at"))}
        if cursor_key == "cloud_pull":
            return {"last_pull_at": safe_timestamp(payload.get("last_pull_at"))}
        if cursor_key == "cloud_success":
            return {"last_success_at": safe_timestamp(payload.get("last_success_at"))}
        if cursor_key == "cloud_ack":
            token = payload.get("last_ack_token")
            return {"last_ack_token": str(token)[:512] if isinstance(token, str) else None}
        error = payload.get("last_error")
        return {
            "last_error": safe_error_code(error),
            "last_error_fingerprint": safe_fingerprint(
                payload.get("last_error_fingerprint"), fallback_value=error,
            ),
            "updated_at": safe_timestamp(payload.get("updated_at")) or utc_now_iso(),
        }

    def _scrub_legacy_content(self) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT cursor_key, payload_json FROM sync_cursors"
            ).fetchall()
            for row in rows:
                key = str(row["cursor_key"])
                if key not in _ALLOWED_CURSOR_KEYS:
                    conn.execute("DELETE FROM sync_cursors WHERE cursor_key = ?", (key,))
                    continue
                try:
                    raw = json.loads(row["payload_json"])
                except Exception:
                    raw = {}
                raw = raw if isinstance(raw, dict) else {}
                conn.execute(
                    "UPDATE sync_cursors SET payload_json = ?, updated_at = ? WHERE cursor_key = ?",
                    (json.dumps(self._sanitize_payload(key, raw)), utc_now_iso(), key),
                )
            conn.commit()
            conn.execute("VACUUM")

    def upsert(self, cursor_key: str, payload: Dict[str, Any]) -> None:
        if cursor_key not in _ALLOWED_CURSOR_KEYS:
            raise ValueError(f"unsupported_sync_cursor_key:{cursor_key}")
        payload = self._sanitize_payload(cursor_key, payload)
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_cursors (cursor_key, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cursor_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    cursor_key,
                    json.dumps(payload, ensure_ascii=False),
                    now,
                ),
            )
            conn.commit()

    def get(self, cursor_key: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM sync_cursors
                WHERE cursor_key = ?
                """,
                (cursor_key,),
            ).fetchone()

        if not row:
            return {}

        try:
            payload = json.loads(row["payload_json"])
        except Exception:
            return {}

        return payload if isinstance(payload, dict) else {}

    def delete(self, cursor_key: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM sync_cursors WHERE cursor_key = ?",
                (cursor_key,),
            )
            conn.commit()

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT cursor_key, payload_json
                FROM sync_cursors
                ORDER BY cursor_key ASC
                """
            ).fetchall()

        out: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            try:
                parsed = json.loads(row["payload_json"])
                out[row["cursor_key"]] = parsed if isinstance(parsed, dict) else {}
            except Exception:
                out[row["cursor_key"]] = {}
        return out

    def get_last_push_at(self) -> Optional[str]:
        value = self.get("cloud_push")
        last_push_at = value.get("last_push_at")
        return last_push_at if isinstance(last_push_at, str) else None

    def set_last_push_at(self, ts: str) -> None:
        payload = self.get("cloud_push")
        payload["last_push_at"] = ts
        self.upsert("cloud_push", payload)

    def get_last_pull_at(self) -> Optional[str]:
        value = self.get("cloud_pull")
        last_pull_at = value.get("last_pull_at")
        return last_pull_at if isinstance(last_pull_at, str) else None

    def set_last_pull_at(self, ts: str) -> None:
        payload = self.get("cloud_pull")
        payload["last_pull_at"] = ts
        self.upsert("cloud_pull", payload)

    def get_last_ack_token(self) -> Optional[str]:
        value = self.get("cloud_ack")
        token = value.get("last_ack_token")
        return token if isinstance(token, str) else None

    def set_last_ack_token(self, token: str) -> None:
        payload = self.get("cloud_ack")
        payload["last_ack_token"] = token
        self.upsert("cloud_ack", payload)

    def get_last_success_at(self) -> Optional[str]:
        value = self.get("cloud_success")
        ts = value.get("last_success_at")
        return ts if isinstance(ts, str) else None

    def set_last_success_at(self, ts: str) -> None:
        payload = self.get("cloud_success")
        payload["last_success_at"] = ts
        self.upsert("cloud_success", payload)

    def get_last_error(self) -> Optional[str]:
        value = self.get("cloud_error")
        error = value.get("last_error")
        return error if isinstance(error, str) else None

    def set_last_error(self, error: str) -> None:
        self.upsert("cloud_error", {"last_error": error, "updated_at": utc_now_iso()})

    def clear_last_error(self) -> None:
        payload = self.get("cloud_error")
        payload["last_error"] = None
        payload["updated_at"] = utc_now_iso()
        self.upsert("cloud_error", payload)
