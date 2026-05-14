# backend/routes/aion_akg_demo_api.py
from __future__ import annotations

import os, json, time
from threading import Lock
from typing import Any, Dict, List

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.modules.aion_cognition.akg_triplets import AKGTripletStore
from backend.modules.aion_cognition.akg_graph_export import export_akg_graph
from backend.modules.aion_cognition.demo5_akg_consolidation import _load_lexmemory_pairs  # reuse loader

router = APIRouter(tags=["AION Demo AKG"])

_LOCK = Lock()
_STORE = AKGTripletStore()  # uses data/knowledge/akg_triplets.json by default

GRAPH_PATH = "data/telemetry/demo5_akg_graph.json"
TIMELINE_PATH = "data/telemetry/demo5_akg_timeline.json"
LEX_PATH_DEFAULT = "data/memory/lex_memory.json"

def _ensure_dirs():
    os.makedirs("data/telemetry", exist_ok=True)
    os.makedirs("data/knowledge", exist_ok=True)

@router.get("/api/akg")
def get_akg(topk: int = Query(12, ge=1, le=100)) -> Dict[str, Any]:
    _ensure_dirs()
    with _LOCK:
        return _STORE.snapshot(k=int(topk))

@router.get("/api/akg/graph")
def get_akg_graph() -> JSONResponse:
    _ensure_dirs()
    with _LOCK:
        export_akg_graph(_STORE, GRAPH_PATH)
        try:
            return JSONResponse(json.loads(open(GRAPH_PATH, "r", encoding="utf-8").read()))
        except Exception:
            return JSONResponse({"version": 1, "nodes": [], "links": [], "ts": time.time()})

@router.post("/api/demo/akg/reset")
def akg_reset() -> Dict[str, Any]:
    _ensure_dirs()
    with _LOCK:
        _STORE.clear()
        export_akg_graph(_STORE, GRAPH_PATH)
        return {"ok": True, "ts": time.time(), "edges_total": 0}

@router.post("/api/demo/akg/step")
def akg_step(
    lex: str = Query(LEX_PATH_DEFAULT),
    alpha: float = Query(0.35),
    half_life_s: float = Query(0.0),
) -> Dict[str, Any]:
    _ensure_dirs()
    with _LOCK:
        # update store parameters live (keeps file stable)
        _STORE.alpha = float(alpha)
        _STORE.half_life_s = float(half_life_s)

        triplets = _load_lexmemory_pairs(lex)
        if not triplets:
            triplets = [
                ("AION", "is", "alive"),
                ("AION", "learns_via", "CEE"),
                ("LexMemory", "reinforces", "AKG"),
                ("MeaningField", "vectorizes_to", "qphoto"),
                ("QQC", "feeds_back", "delta_ops"),
            ]

        # round-robin step index stored in timeline file (cheap persistent cursor)
        idx = 0
        try:
            if os.path.exists(TIMELINE_PATH):
                raw = json.loads(open(TIMELINE_PATH, "r", encoding="utf-8").read())
                idx = int(raw.get("_cursor", 0))
        except Exception:
            idx = 0

        t = triplets[idx % len(triplets)]
        e = _STORE.reinforce(*t, hit=1.0)
        _STORE.save()

        export_akg_graph(_STORE, GRAPH_PATH)

        # persist cursor
        try:
            with open(TIMELINE_PATH, "w", encoding="utf-8") as f:
                json.dump({"_cursor": idx + 1, "ts": time.time()}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return {
            "ok": True,
            "ts": time.time(),
            "reinforced": {"s": e.s, "r": e.r, "o": e.o, "strength": e.strength, "count": e.count},
            "edges_total": len(_STORE.edges),
        }

@router.post("/api/demo/akg/run")
def akg_run(
    rounds: int = Query(200, ge=1, le=20000),
    lex: str = Query(LEX_PATH_DEFAULT),
    alpha: float = Query(0.35),
    half_life_s: float = Query(0.0),
    topk: int = Query(12, ge=1, le=100),
) -> Dict[str, Any]:
    _ensure_dirs()
    with _LOCK:
        _STORE.alpha = float(alpha)
        _STORE.half_life_s = float(half_life_s)

        triplets = _load_lexmemory_pairs(lex)
        if not triplets:
            triplets = [
                ("AION", "is", "alive"),
                ("AION", "learns_via", "CEE"),
                ("LexMemory", "reinforces", "AKG"),
                ("MeaningField", "vectorizes_to", "qphoto"),
                ("QQC", "feeds_back", "delta_ops"),
            ]

        for i in range(int(rounds)):
            t = triplets[i % len(triplets)]
            _STORE.reinforce(*t, hit=1.0)

        _STORE.save()
        export_akg_graph(_STORE, GRAPH_PATH)
        return {"ok": True, **_STORE.snapshot(k=int(topk))}