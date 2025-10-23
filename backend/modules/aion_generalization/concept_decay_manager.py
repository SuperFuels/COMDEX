#!/usr/bin/env python3
"""
♻️  Aion Concept Decay Manager — Phase 35.2
───────────────────────────────────────────────────────────────────────────────
Scans AKG for obsolete or weak links (low strength, old timestamp),
decays or removes them, and exports a snapshot for evolution visualization.

• Reads reinforcement history from concept_reinforcement.log
• Decays neglected concept edges
• Exports summary for evolution_dashboard
"""

import json, time, sqlite3
from pathlib import Path
from backend.modules.aion_knowledge import knowledge_graph_core as akg

DB_PATH = Path("data/knowledge/aion_knowledge_graph.db")
REINFORCE_LOG = Path("data/feedback/concept_reinforcement.log")
SNAPSHOT_PATH = Path("data/feedback/concept_evolution_snapshot.jsonl")

# ─────────────────────────────────────────────
# Parameters
# ─────────────────────────────────────────────
DECAY_INTERVAL = 3600 * 4        # 4 hours without reinforcement → decay
DECAY_FACTOR = 0.97              # decay multiplier
MIN_STRENGTH = 0.25              # remove links weaker than this
EXPORT_LIMIT = 1000

def parse_reinforcement_log():
    """Return {concept_name: last_timestamp} dict."""
    if not REINFORCE_LOG.exists():
        return {}
    last_seen = {}
    with REINFORCE_LOG.open() as f:
        for line in f:
            try:
                ts, msg = line.strip().split(" ", 1)
                if msg.startswith("reinforce"):
                    cname = msg.split()[1]
                    last_seen[cname] = float(ts)
            except Exception:
                continue
    return last_seen

def decay_stale_links(last_seen: dict):
    """Decay or remove stale 'is_a' links in AKG."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    table = "triplets" if "triplets" in tables else "knowledge"

    cur.execute(f"SELECT subject,predicate,object,strength,timestamp FROM {table} WHERE predicate='is_a'")
    rows = cur.fetchall()
    now = time.time()
    updates, deletions = 0, 0

    for s,p,o,w,ts in rows:
        cname = o.replace("concept:", "")
        t_last = last_seen.get(cname, 0)
        age = now - t_last
        if age > DECAY_INTERVAL:
            new_strength = w * DECAY_FACTOR
            if new_strength < MIN_STRENGTH:
                cur.execute(f"DELETE FROM {table} WHERE subject=? AND object=?", (s,o))
                deletions += 1
            else:
                cur.execute(f"UPDATE {table} SET strength=? WHERE subject=? AND object=?", (new_strength,s,o))
                updates += 1
    conn.commit()
    conn.close()
    print(f"⚖️  Decayed {updates} links, removed {deletions} obsolete edges.")
    return updates, deletions

def export_snapshot():
    """Write current AKG concept snapshot for visualization."""
    concepts = akg.export_concepts()
    snapshot = {
        "timestamp": time.time(),
        "concepts": {k: len(v) for k, v in concepts.items()}
    }
    with SNAPSHOT_PATH.open("a") as f:
        f.write(json.dumps(snapshot) + "\n")
    print(f"📤 Snapshot written to {SNAPSHOT_PATH} ({len(concepts)} concepts).")

def main():
    print("🧹 Running Aion Concept Decay Manager (Phase 35.2)…")
    last_seen = parse_reinforcement_log()
    decay_stale_links(last_seen)
    export_snapshot()
    print("✅ Obsolete-link decay cycle complete.")

if __name__ == "__main__":
    main()