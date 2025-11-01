#!/usr/bin/env python3
"""
Phase 1 - Encode Trial Logs into the Aion Knowledge Graph
────────────────────────────────────────────────────────────
Reads trial results JSONL (choice, ans, conf, acc)
-> Creates nodes and weighted edges in Aion's Knowledge Graph.
"""

import json, time
from pathlib import Path

try:
    from aion_knowledge.knowledge_graph_core import add_triplet
except Exception:
    def add_triplet(a,b,c,**kw):
        print(f"add_triplet({a},{b},{c},{kw})")

TRIAL_LOG = Path("data/curriculum/perception_shapes.jsonl")  # or wherever your JSON lines are

def encode_trials():
    if not TRIAL_LOG.exists():
        print(f"❌ No trial log at {TRIAL_LOG}")
        return

    print(f"🧠 Encoding trials from {TRIAL_LOG}")
    with open(TRIAL_LOG) as f:
        for line in f:
            if not line.strip(): continue
            j = json.loads(line)
            i     = j.get("i")
            choice= j.get("choice")
            ans   = j.get("ans")
            acc   = float(j.get("acc",0))
            conf  = float(j.get("conf",0))

            trial_node = f"trial:{i}"
            add_triplet(trial_node, "observed_choice", f"glyph:{choice}", strength=conf)
            add_triplet(trial_node, "expected_answer", f"glyph:{ans}",   strength=1.0)
            add_triplet(f"glyph:{choice}", "reinforced_by", trial_node,  strength=acc)
            add_triplet(f"glyph:{ans}",    "target_of",     trial_node,  strength=acc)
    print("✅ Knowledge graph updated from trials.")

if __name__ == "__main__":
    encode_trials()