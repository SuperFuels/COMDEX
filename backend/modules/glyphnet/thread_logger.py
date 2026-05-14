# backend/modules/glyphnet/thread_logger.py
from __future__ import annotations
import json
import os
import sqlite3
import time
from typing import Dict, Any, List

# Configure where the tiny DB lives (override via env if you like)
DB_PATH = os.getenv("GLYPH_THREADLOG_DB", "data/threadlog.sqlite")


def _db() -> sqlite3.Connection:
    """
    Create/open the thread log database and ensure schema exists.
    Safe to call many times; returns a shared connection with simple pragmas.
    """
    # Ensure parent folder exists; handle cases where DB_PATH has no directory
    parent = os.path.dirname(DB_PATH) or "."
    os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Small durability/throughput tune for a local dev DB
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          topic TEXT NOT NULL,
          graph TEXT NOT NULL,          -- "personal" | "work" | future scopes
          type  TEXT NOT NULL,          -- "text" | "voice"
          ts    REAL NOT NULL,          -- unix seconds (float)
          direction TEXT NOT NULL,      -- "in" | "out"
          sender TEXT,                  -- from
          recipient TEXT,               -- to
          payload TEXT NOT NULL         -- JSON blob (text, mime, seq, channel, bytes_b64, etc.)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_events_tg ON events(topic, graph, ts)")
    return conn


def log_thread_event(
    topic: str,
    event: Dict[str, Any],
    direction: str = "out",
    user_id: str = "server",
) -> None:
    """
    Append one event to the log.

    Expected `event` fields:
      {
        "graph": "personal" | "work" (default "personal"),
        "type":  "text" | "voice",
        "ts":    float (unix seconds; will default to now),
        "from":  str,
        "to":    str,
        "payload": { ... }  # e.g., {"text":"hi"} or {"mime":"audio/webm","seq":0,"channel":"...","bytes_b64":"..."}
      }
    """
    conn = _db()
    conn.execute(
        "INSERT INTO events(topic, graph, type, ts, direction, sender, recipient, payload) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            topic,
            (event.get("graph") or "personal").lower(),
            event["type"],
            float(event.get("ts", time.time())),
            direction,
            event.get("from"),
            event.get("to"),
            json.dumps(event.get("payload") or {}),
        ),
    )
    conn.commit()


def read_thread(topic: str, graph: str = "personal", limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch the most recent `limit` events for (topic, graph), returned oldest → newest.
    """
    conn = _db()
    cur = conn.execute(
        "SELECT id, type, ts, direction, sender, recipient, payload "
        "FROM events WHERE topic=? AND graph=? "
        "ORDER BY ts DESC LIMIT ?",
        (topic, (graph or "personal").lower(), int(limit)),
    )

    out: List[Dict[str, Any]] = []
    for row in cur.fetchall():
        payload = json.loads(row[6] or "{}")
        out.append(
            {
                "id": row[0],
                "type": row[1],
                "ts": row[2],
                "direction": row[3],
                "from": row[4],
                "to": row[5],
                "payload": payload,
            }
        )

    # DB returns newest → oldest; invert to oldest → newest for UI merging
    return list(reversed(out))