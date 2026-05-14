# backend/modules/knowledge_graph/ledger_replay.py
import os, json, urllib.request
from typing import Optional
from backend.modules.knowledge_graph.knowledge_graph_writer import kg_writer

LEDGER_QUERY = os.getenv("KG_LEDGER_QUERY", "http://localhost:3000/api/kg/query")

def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))

def replay_into_container(container_id: str, kg: str, owner: str, thread_id: Optional[str] = None):
    cursor = None
    while True:
        qs = f"?kg={kg}&limit=500"
        if thread_id: qs += f"&thread_id={thread_id}"
        if cursor: qs += f"&after={cursor}"
        data = _get(LEDGER_QUERY + qs)
        items = data.get("items", [])
        if not items:
            break

        for ev in items:
            p = ev["payload"]
            gtype = p.get("glyph_type") or ev.get("type")
            # only rebuild entries we know how to map
            if gtype in ("message","kg_node","kg_edge","self_reflection","predictive","glyph"):
                kg_writer.inject_glyph(
                    content=p.get("content") or p.get("text") or {"type":"symbol","text":"∅"},
                    glyph_type=gtype if gtype != "message" else "glyph",
                    metadata=p.get("metadata"),
                    agent_id=p.get("agent_id","replay"),
                    tags=p.get("tags") or [],
                )
        cursor = data.get("next_cursor")
        if not cursor:
            break