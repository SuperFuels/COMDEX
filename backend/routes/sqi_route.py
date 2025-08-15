# -*- coding: utf-8 -*-
# backend/routes/sqi_route.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.modules.sqi.sqi_container_registry import sqi_registry
from backend.modules.glyphos.ghx_export import encode_glyphs_to_ghx

router = APIRouter(prefix="/sqi", tags=["SQI-Routing"])

# In-memory weights (tweak at runtime); keep defaults sane.
_WEIGHTS: Dict[str, float] = {
    "freshness": 0.35,   # newer updated containers win
    "domain_match": 0.40,# exact domain kind
    "size_penalty": 0.10,# very large containers score lower for speed
    "priority_hint": 0.15# explicit 'priority' meta wins
}

class RouteReq(BaseModel):
    domain: str
    kind: str = "fact"
    hint: Optional[str] = None

class WeightPatch(BaseModel):
    weights: Dict[str, float]

def _score(entry: Dict[str, Any], req: RouteReq) -> Dict[str, Any]:
    meta = (entry.get("meta") or {})
    s = 0.0
    breakdown = {}

    # Domain match
    dm = 1.0 if entry.get("domain") == req.domain and entry.get("type") == "container" and entry.get("kind") == req.kind else 0.0
    breakdown["domain_match"] = dm * _WEIGHTS["domain_match"]; s += breakdown["domain_match"]

    # Freshness (if last_updated present)
    lu = meta.get("last_updated")
    fr = 0.75 if lu else 0.2
    breakdown["freshness"] = fr * _WEIGHTS["freshness"]; s += breakdown["freshness"]

    # Size penalty (prefer smaller unless hint says otherwise)
    approx_nodes = int(meta.get("hov", {}).get("reason", {}).get("nodes", 0))
    sp = 1.0 if approx_nodes < 200 else 0.6 if approx_nodes < 1000 else 0.3
    breakdown["size_penalty"] = sp * _WEIGHTS["size_penalty"]; s += breakdown["size_penalty"]

    # Priority hint
    ph = float(meta.get("priority", 0.0))
    breakdown["priority_hint"] = min(1.0, max(0.0, ph)) * _WEIGHTS["priority_hint"]; s += breakdown["priority_hint"]

    return {"score": round(s, 6), "breakdown": breakdown}

@router.get("/route")
def choose_route(domain: str, kind: str = "fact", hint: str | None = None):
    # list registered candidates
    try:
        entries = sqi_registry.list(domain=domain, kind=kind)  # implement .list(...) if you don’t already; otherwise get all and filter
    except Exception:
        entries = sqi_registry.list_all()  # fallback then filter
        entries = [e for e in entries if e.get("domain") == domain and e.get("kind") == kind]

    if not entries:
        raise HTTPException(404, f"No candidates for domain='{domain}', kind='{kind}'")

    req = RouteReq(domain=domain, kind=kind, hint=hint)
    ranked = []
    for e in entries:
        sc = _score(e, req)
        ranked.append({"entry": e, **sc})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    choice = ranked[0]
    return {"status": "ok", "choice": choice, "candidates": ranked[:10], "weights": _WEIGHTS}

@router.post("/route/weights")
def patch_weights(patch: WeightPatch):
    global _WEIGHTS
    # normalize and clamp to [0..1] basic safety
    for k, v in patch.weights.items():
        if k in _WEIGHTS:
            try:
                _WEIGHTS[k] = float(max(0.0, min(1.0, v)))
            except Exception:
                pass
    return {"status": "ok", "weights": _WEIGHTS}

from fastapi import APIRouter, HTTPException
from backend.modules.dimensions.containers.container_loader import load_decrypted_container
from backend.modules.glyphos.ghx_export import encode_glyphs_to_ghx

router = APIRouter(prefix="/sqi", tags=["SQI"])

@router.get("/ghx/encode/{container_id}")
def encode_container_to_ghx(container_id: str):
    container = load_decrypted_container(container_id)
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    ghx = encode_glyphs_to_ghx(container)
    return {"ghx": ghx}