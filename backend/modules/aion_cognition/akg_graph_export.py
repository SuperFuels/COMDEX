# backend/modules/aion_cognition/akg_graph_export.py
from __future__ import annotations
from typing import Dict, Any
import os, json, time
from .akg_triplets import AKGTripletStore

def export_akg_graph(store: AKGTripletStore, out_path: str) -> str:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    node_id: Dict[str, str] = {}
    nodes = []

    def nid(label: str) -> str:
        if label not in node_id:
            node_id[label] = f"n{len(node_id) + 1}"
            nodes.append({"id": node_id[label], "label": label})
        return node_id[label]

    links = []
    for e in store.edges.values():
        a = nid(e.s)
        b = nid(e.o)
        thickness = 1.0 + 8.0 * float(e.strength)  # 1..9
        glow = float(e.strength)                   # 0..1

        links.append({
            "source": a,
            "target": b,
            "predicate": e.r,
            "strength": e.strength,
            "count": e.count,
            "thickness": thickness,
            "glow": glow,
            "last_ts": e.last_ts,
        })

    payload: Dict[str, Any] = {
        "version": 1,
        "ts": time.time(),
        "nodes": nodes,
        "links": links,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path