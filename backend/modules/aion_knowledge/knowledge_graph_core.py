#!/usr/bin/env python3
"""
Aion Knowledge Graph Core (AKG)
───────────────────────────────────────────────
Persistent symbolic–resonant memory substrate for Aion.

• Stores triplets: (subject, predicate, object, strength, vec, timestamp)
• Triplets represent symbolic–resonant associations learned by PAL, RAL, TCFK.
• Provides semantic search, reinforcement, and recall.

Backend: lightweight SQLite (local) for permanence and speed.
"""

import sqlite3, json, math, time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Optional

# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────
DATA_PATH = Path("data/knowledge")
DATA_PATH.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_PATH / "aion_knowledge_graph.db"

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            predicate TEXT,
            object TEXT,
            strength REAL,
            vec TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    return conn


# ─────────────────────────────────────────────
# Core Operations
# ─────────────────────────────────────────────
def add_triplet(subject: str, predicate: str, obj: str,
                vec: Optional[list] = None,
                strength: float = 1.0):
    """Add or reinforce a triplet."""
    ts = datetime.now(timezone.utc).isoformat()
    vec_json = json.dumps(vec) if vec else None
    conn = _connect()

    # If exists, reinforce instead of duplicate
    cur = conn.execute(
        "SELECT id, strength FROM knowledge WHERE subject=? AND predicate=? AND object=?",
        (subject, predicate, obj)
    )
    row = cur.fetchone()
    if row:
        new_strength = row[1] + 0.1 * strength
        conn.execute("UPDATE knowledge SET strength=?, timestamp=? WHERE id=?",
                     (new_strength, ts, row[0]))
    else:
        conn.execute(
            "INSERT INTO knowledge (subject,predicate,object,strength,vec,timestamp) VALUES (?,?,?,?,?,?)",
            (subject, predicate, obj, strength, vec_json, ts)
        )
    conn.commit()
    conn.close()


def search(subject: Optional[str] = None,
           predicate: Optional[str] = None,
           obj: Optional[str] = None) -> List[dict]:
    """Search for matching triplets."""
    conn = _connect()
    q = "SELECT subject,predicate,object,strength,vec,timestamp FROM knowledge WHERE 1=1"
    params = []
    if subject:
        q += " AND subject=?"; params.append(subject)
    if predicate:
        q += " AND predicate=?"; params.append(predicate)
    if obj:
        q += " AND object=?"; params.append(obj)

    cur = conn.execute(q, tuple(params))
    rows = [
        {
            "subject": r[0],
            "predicate": r[1],
            "object": r[2],
            "strength": r[3],
            "vec": json.loads(r[4]) if r[4] else None,
            "timestamp": r[5]
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


def reinforce(subject: str, predicate: str, obj: str, gain: float = 0.05):
    """Increment the strength of an existing link."""
    conn = _connect()
    cur = conn.execute(
        "SELECT id, strength FROM knowledge WHERE subject=? AND predicate=? AND object=?",
        (subject, predicate, obj)
    )
    row = cur.fetchone()
    if row:
        new_strength = row[1] + gain
        conn.execute("UPDATE knowledge SET strength=? WHERE id=?", (new_strength, row[0]))
        conn.commit()
    conn.close()


def related(node: str, depth: int = 1) -> List[dict]:
    """Find all related triplets (either as subject or object)."""
    conn = _connect()
    cur = conn.execute("""
        SELECT subject,predicate,object,strength,vec,timestamp
        FROM knowledge
        WHERE subject=? OR object=?
        ORDER BY strength DESC
        LIMIT 100
    """, (node, node))
    rows = [
        {
            "subject": r[0],
            "predicate": r[1],
            "object": r[2],
            "strength": r[3],
            "vec": json.loads(r[4]) if r[4] else None,
            "timestamp": r[5]
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


def dump_summary(limit: int = 10):
    """Display strongest knowledge links."""
    conn = _connect()
    cur = conn.execute(
        "SELECT subject,predicate,object,strength FROM knowledge ORDER BY strength DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    print("🧩 Top Knowledge Links:")
    for s,p,o,w in rows:
        print(f"  {s} —[{p}:{w:.3f}]→ {o}")