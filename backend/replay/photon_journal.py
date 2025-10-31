# backend/replay/photon_journal.py

import os, json, time
from typing import Dict, Any, Iterable

JOURNAL_PATH = "data/replay/photon_journal.jsonl"

os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)

def append_event(ev: Dict[str, Any]):
    ev["t"] = ev.get("t", time.time())
    with open(JOURNAL_PATH, "a") as f:
        f.write(json.dumps(ev) + "\n")

def load_events() -> Iterable[Dict[str, Any]]:
    if not os.path.exists(JOURNAL_PATH):
        return []
    with open(JOURNAL_PATH) as f:
        for line in f:
            yield json.loads(line.strip())