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

def dump_concepts(limit: int = 20):
    """Display all 'is_a' concept relations for verification."""
    conn = _connect()
    cur = conn.execute("""
        SELECT subject, predicate, object, strength
        FROM knowledge
        WHERE predicate='is_a'
        ORDER BY strength DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    print("🌐 Concept Field Relations:")
    for s, p, o, w in rows:
        print(f"  {s} —[{p}:{w:.3f}]→ {o}")


import uuid
import time
import logging

logger = logging.getLogger(__name__)

def create_concept_node(name: str, symbols: list[str], meta: dict | None = None) -> str:
    """
    Create a new concept node in the Aion Knowledge Graph (AKG).

    Args:
        name: Human-readable concept name.
        symbols: List of associated symbols or glyphs.
        meta: Optional metadata (e.g., {"origin": "fusion", "rsi_mean": 0.42, ...})

    Returns:
        concept_id (str): The unique concept node ID created in the AKG.
    """
    global triplets

    # Ensure AKG triplet store is loaded
    try:
        if not triplets:
            load_knowledge()
    except NameError:
        load_knowledge()

    concept_id = f"concept:{name}_{uuid.uuid4().hex[:8]}"
    ts = time.time()

    # Core node definition
    triplets[(concept_id, "type", "concept")] = 1.0
    triplets[(concept_id, "created_at", str(ts))] = 1.0

    # Link associated symbols
    if symbols:
        for sym in symbols:
            triplets[(f"symbol:{sym}", "is_a", concept_id)] = 1.0

    # Metadata embedding
    if meta:
        for k, v in meta.items():
            triplets[(concept_id, f"meta:{k}", str(v))] = 1.0

    # Add system provenance marker
    triplets[(concept_id, "meta:origin_system", "AION.ConceptEvolution")] = 1.0

    # Persistence layer
    try:
        save_knowledge()
    except Exception as e:
        logger.warning(f"[AKG] Could not save concept node {concept_id}: {e}")

    logger.info(
        f"[AKG] Created concept node: {concept_id} "
        f"({len(symbols) if symbols else 0} symbols, meta={len(meta) if meta else 0})"
    )

    return concept_id
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# Knowledge Graph Loader + Exporter
# ─────────────────────────────────────────────
triplets = {}  # In-memory cache of (subject, predicate, object) → strength

def load_knowledge():
    """
    Load all triplets from the SQLite knowledge DB into memory.
    Ensures global triplet cache is populated.
    """
    global triplets
    conn = _connect()
    cur = conn.execute("SELECT subject, predicate, object, strength FROM knowledge")
    rows = cur.fetchall()
    conn.close()

    triplets = {(s, p, o): w for s, p, o, w in rows}

def save_knowledge():
    """Persist all in-memory triplets to the SQLite knowledge database."""
    global triplets
    conn = _connect()
    conn.execute("DELETE FROM knowledge")  # simple full sync
    for (s, p, o), w in triplets.items():
        conn.execute(
            "INSERT INTO knowledge (subject, predicate, object, strength, timestamp) VALUES (?, ?, ?, ?, ?)",
            (s, p, o, w, datetime.now(timezone.utc).isoformat())
        )
    conn.commit()
    conn.close()

def export_concepts() -> dict[str, list[str]]:
    """
    Export a mapping of concept → [symbols] from the current AKG triplet store.

    - Automatically loads triplets if not yet in memory.
    - Returns a dict where each concept maps to its associated symbol list.

    Example:
        {
            "concept_energy": ["Φ", "Ω", "λ"],
            "concept_field": ["ψ", "A", "S"]
        }
    """
    global triplets

    # Ensure triplet store is loaded
    if not triplets:
        load_knowledge()

    concept_map: dict[str, list[str]] = {}

    for (s, p, o), w in triplets.items():
        if p == "is_a" and s.startswith("symbol:") and o.startswith("concept:"):
            sym = s.split("symbol:", 1)[1]
            concept = o.split("concept:", 1)[1]
            concept_map.setdefault(concept, []).append(sym)

    return concept_map

def inspect_node(concept_name: str):
    """
    Inspect all triplets and metadata related to a concept node.

    Example:
        inspect_node("superconcept_1761236835")
    """
    global triplets
    if not triplets:
        load_knowledge()

    concept_id = f"concept:{concept_name}" if not concept_name.startswith("concept:") else concept_name
    print(f"🔍 Inspecting {concept_id}...\n")

    related_entries = [
        (s, p, o, w)
        for (s, p, o), w in triplets.items()
        if s == concept_id or o == concept_id
    ]

    if not related_entries:
        print("⚠️ No related entries found.")
        return

    for s, p, o, w in related_entries:
        arrow = "→" if s == concept_id else "←"
        print(f"  {s} {arrow} [{p}:{w}] {o}")

def print_concept_tree(limit: int = 50, indent: int = 0):
    """
    Print a hierarchical tree of all concepts and their derived links (subclass_of).
    Traverses the AKG triplets to visualize fusion lineage.
    """
    global triplets
    if not triplets:
        load_knowledge()

    # Build adjacency from subclass_of relationships
    tree = {}
    for (s, p, o), w in triplets.items():
        if p == "subclass_of":
            parent = o.replace("concept:", "")
            child = s.replace("concept:", "")
            tree.setdefault(parent, []).append(child)

    def _print_branch(node, depth=0, seen=None):
        if seen is None:
            seen = set()
        if node in seen:
            return
        seen.add(node)
        prefix = "  " * depth + ("↳ " if depth else "")
        print(f"{prefix}{node}")
        for child in tree.get(node, []):
            _print_branch(child, depth + 1, seen)

    roots = [n for n in tree if not any(n in c for c in tree.values())]
    print("🌳 Concept Hierarchy:")
    count = 0
    for r in roots:
        _print_branch(r)
        count += 1
        if count >= limit:
            break
    if count == 0:
        print("⚠️ No subclass_of relationships found.")

def adjust_concept_strength(concept_name: str, delta: float, mode: str = "add"):
    """
    Adjust all 'is_a' edge strengths toward a given concept by delta.
    Compatible with both 'triplets' and legacy 'knowledge' table schemas.
    """
    import sqlite3
    db_path = "data/knowledge/aion_knowledge_graph.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Detect schema
    tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    table_name = "triplets" if "triplets" in tables else "knowledge"

    if mode == "add":
        cur.execute(f"""
            UPDATE {table_name}
            SET strength = strength + ?
            WHERE object = ? AND predicate = 'is_a'
        """, (delta, f"concept:{concept_name}"))
    elif mode == "scale":
        cur.execute(f"""
            UPDATE {table_name}
            SET strength = strength * ?
            WHERE object = ? AND predicate = 'is_a'
        """, (delta, f"concept:{concept_name}"))

    conn.commit()
    conn.close()

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

# ─────────────────────────────────────────────
# Test harness (manual verification)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from backend.modules.aion_knowledge import knowledge_graph_core as akg
    concepts = akg.export_concepts()
    print("📘 Current AKG concepts:")
    print(concepts.keys())
    print(f"Total concepts: {len(concepts)}")