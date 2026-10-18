from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List
from uuid import uuid4

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


DEFAULT_DB_PATH = Path(os.getenv("GLYPH_THREADLOG_DB", "data/threadlog.sqlite"))


class GlyphThreadStore:
    """Workspace-scoped GlyphNet communication history.

    In Guardian mode complete text/voice payloads are encrypted records in the
    external Business Vault. An explicit SQLite path remains available only
    for legacy operation, tests and source-retaining migration.
    """

    RECORD_TYPE = "glyphnet_thread_event"
    DOMAIN_ID = "business.knowledge_audit"

    def __init__(
        self,
        *,
        domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
        legacy_db_path: str | Path | None = None,
        auto_configure: bool = True,
    ) -> None:
        if domain_store is None and auto_configure and legacy_db_path is None:
            if guardian_mode_requested():
                runtime = configured_business_vault_runtime()
                domain_store = VaultDomainStore(
                    runtime.guardian, actor_id="glyphnet-thread-runtime"
                )
        self.domain_store = domain_store
        self.workspace_id = str(
            workspace_id
            or os.environ.get("TESSARIS_BUSINESS_STABLE_ID")
            or ""
        ).strip()
        if self.domain_store is not None and not self.workspace_id:
            raise ValueError("glyphnet_thread_workspace_id_required")
        self.legacy_db_path = Path(legacy_db_path or DEFAULT_DB_PATH)

    @property
    def guardian_enabled(self) -> bool:
        return self.domain_store is not None

    def _legacy_connection(self) -> sqlite3.Connection:
        self.legacy_db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.legacy_db_path)
        try:
            connection.execute("PRAGMA journal_mode=WAL;")
            connection.execute("PRAGMA synchronous=NORMAL;")
        except sqlite3.DatabaseError:
            pass
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              topic TEXT NOT NULL,
              graph TEXT NOT NULL,
              type TEXT NOT NULL,
              ts REAL NOT NULL,
              direction TEXT NOT NULL,
              sender TEXT,
              recipient TEXT,
              user_id TEXT,
              payload TEXT NOT NULL
            )
            """
        )
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(events)").fetchall()
        }
        if "user_id" not in columns:
            connection.execute("ALTER TABLE events ADD COLUMN user_id TEXT")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_events_tg ON events(topic, graph, ts)"
        )
        return connection

    def append(
        self,
        topic: str,
        event: Dict[str, Any],
        *,
        direction: str = "out",
        user_id: str = "server",
    ) -> None:
        timestamp = float(event.get("ts", time.time()))
        payload = {
            "record_type": self.RECORD_TYPE,
            "topic": str(topic),
            "graph": str(event.get("graph") or "personal").lower(),
            "type": str(event["type"]),
            "ts": timestamp,
            "direction": str(direction),
            "sender": event.get("from"),
            "recipient": event.get("to"),
            "user_id": str(user_id),
            "payload": dict(event.get("payload") or {}),
        }
        if self.domain_store is not None:
            entity_id = f"glyphnet-thread-{time.time_ns()}-{uuid4().hex}"
            self.domain_store.put(
                self.DOMAIN_ID,
                workspace_id=self.workspace_id,
                entity_id=entity_id,
                payload=payload,
                expected_version=None,
                idempotency_key=f"glyphnet-thread-{uuid4().hex}",
                actor_id="glyphnet-thread-runtime",
            )
            return

        connection = self._legacy_connection()
        try:
            connection.execute(
                "INSERT INTO events(topic, graph, type, ts, direction, sender, "
                "recipient, user_id, payload) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    payload["topic"],
                    payload["graph"],
                    payload["type"],
                    payload["ts"],
                    payload["direction"],
                    payload["sender"],
                    payload["recipient"],
                    payload["user_id"],
                    json.dumps(payload["payload"]),
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def read(
        self, topic: str, *, graph: str = "personal", limit: int = 100
    ) -> List[Dict[str, Any]]:
        bounded_limit = max(0, min(int(limit), 1000))
        if bounded_limit == 0:
            return []
        graph = str(graph or "personal").lower()
        if self.domain_store is not None:
            rows = []
            for record in self.domain_store.list(
                self.DOMAIN_ID, workspace_id=self.workspace_id
            ):
                payload = record["payload"]
                if (
                    payload.get("record_type") != self.RECORD_TYPE
                    or payload.get("topic") != topic
                    or payload.get("graph") != graph
                ):
                    continue
                rows.append(
                    (float(payload.get("ts") or 0.0), record["entity_id"], payload)
                )
            rows.sort(key=lambda item: (item[0], item[1]))
            return [
                {
                    "id": entity_id,
                    "type": payload["type"],
                    "ts": payload["ts"],
                    "direction": payload["direction"],
                    "from": payload.get("sender"),
                    "to": payload.get("recipient"),
                    "payload": dict(payload.get("payload") or {}),
                }
                for _timestamp, entity_id, payload in rows[-bounded_limit:]
            ]

        connection = self._legacy_connection()
        try:
            cursor = connection.execute(
                "SELECT id, type, ts, direction, sender, recipient, payload "
                "FROM events WHERE topic=? AND graph=? "
                "ORDER BY ts DESC LIMIT ?",
                (topic, graph, bounded_limit),
            )
            output = [
                {
                    "id": row[0],
                    "type": row[1],
                    "ts": row[2],
                    "direction": row[3],
                    "from": row[4],
                    "to": row[5],
                    "payload": json.loads(row[6] or "{}"),
                }
                for row in cursor.fetchall()
            ]
        finally:
            connection.close()
        return list(reversed(output))


def log_thread_event(
    topic: str,
    event: Dict[str, Any],
    direction: str = "out",
    user_id: str = "server",
) -> None:
    GlyphThreadStore().append(topic, event, direction=direction, user_id=user_id)


def read_thread(
    topic: str, graph: str = "personal", limit: int = 100
) -> List[Dict[str, Any]]:
    return GlyphThreadStore().read(topic, graph=graph, limit=limit)
