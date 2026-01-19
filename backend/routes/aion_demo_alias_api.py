from __future__ import annotations

from typing import Any, Callable
from fastapi import APIRouter, HTTPException, Request
from backend.modules.aion_demo import demo_bridge as bridge

router = APIRouter(tags=["AION Proof-of-Life Aliases"])

def _call(name: str, request: Request) -> Any:
    fn: Callable[..., Any] | None = getattr(bridge, name, None)
    if fn is None:
        raise HTTPException(status_code=501, detail=f"demo_bridge missing handler: {name}")
    # if handler accepts request, pass it; else call without args
    try:
        return fn(request)  # type: ignore[misc]
    except TypeError:
        return fn()

@router.get("/api/phi")
def api_phi(request: Request):
    return _call("api_phi", request)

@router.get("/api/adr")
def api_adr(request: Request):
    return _call("api_adr", request)

@router.get("/api/reflex")
def api_reflex(request: Request):
    return _call("api_reflex", request)