from __future__ import annotations
from typing import Dict, Any
import os, json

ROOT = "/workspaces/COMDEX"
WORMHOLE_REG = os.path.join(ROOT, "backend/modules/dna_chain/data/wormhole_registry.json")
CONTAINER_REG = os.path.join(ROOT, "backend/modules/dna_chain/data/container_registry.json")

def _read(p: str) -> Dict[str, Any]:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_wormhole(name: str) -> Dict[str, Any]:
    v = name.strip().lstrip("🌀")
    if v.endswith(".tp"): v = v[:-3]

    wh = _read(WORMHOLE_REG)
    target = None
    for rec in wh.values():
        if str(rec.get("from")) == v:
            target = rec.get("to")
            break

    res = {"ok": False, "from": v, "to": None, "container": None}
    if not target:
        return res

    containers = _read(CONTAINER_REG)
    meta = containers.get(target)
    res["ok"] = bool(meta)
    res["to"] = target
    res["container"] = meta
    return res