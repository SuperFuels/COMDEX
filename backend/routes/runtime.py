# -*- coding: utf-8 -*-
# backend/routes/runtime.py

from __future__ import annotations

import os
import traceback
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.consciousness.state_manager import state_manager

# Prefer the new UCS export; fall back to legacy if needed
try:
    from backend.modules.dimensions.universal_container_system import ucs_runtime  # type: ignore
except Exception:
    from backend.modules.ucs import ucs_runtime  # type: ignore


router = APIRouter()


# ----------------------------
# Runtime Tick Helpers
# ----------------------------
def _run_runtime_tick() -> Any:
    """
    Resolve and run the runtime tick function at call-time.
    Supports multiple historical names to avoid import errors.
    """
    try:
        from backend.modules.runtime import container_runtime as cr
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import container_runtime: {e}")

    candidates = (
        "run_glyph_runtime",  # old name
        "run_runtime",        # alt
        "run_tick",           # alt
        "run_glyph_tick",     # alt
        "run_once",           # alt
    )

    for name in candidates:
        fn = getattr(cr, name, None)
        if callable(fn):
            try:
                return fn(state_manager)
            except Exception as e:
                tb = traceback.format_exc(limit=8)
                raise HTTPException(
                    status_code=500,
                    detail=f"{name} failed: {e}\n--- TRACE ---\n{tb}",
                )

    raise HTTPException(
        status_code=500,
        detail=f"No runtime tick function found in container_runtime. Tried: {candidates}",
    )


# ----------------------------
# Routes
# ----------------------------
@router.post("/api/aion/run-runtime")
def run_runtime_tick() -> Dict[str, Any]:
    """
    Trigger a glyph runtime execution cycle (AION tick).
    """
    print("🌀 [Runtime] Executing glyph runtime tick...")
    _run_runtime_tick()
    return {
        "status": "✅ Glyph runtime tick executed",
        "message": "AION has processed glyphs for this cycle",
    }


@router.post("/ucs/load")
def ucs_load(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load a UCS container from a given path. Optionally register it as an atom.
    Body:
      {
        "path": "path/to/container.json",
        "register_as_atom": true
      }
    """
    path = payload.get("path")
    if not path or not isinstance(path, str):
        raise HTTPException(status_code=400, detail="Missing or invalid 'path'")

    path = os.path.normpath(path)
    register = bool(payload.get("register_as_atom", False))

    try:
        obj = ucs_runtime.load_container_from_path(path, register_as_atom=register)
        if not isinstance(obj, dict):
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected return from loader (type={type(obj).__name__})",
            )
        return {
            "status": "ok",
            "id": obj.get("id"),
            "atom_ids": obj.get("atom_ids", []),
        }
    except Exception as e:
        tb = traceback.format_exc(limit=8)
        raise HTTPException(status_code=400, detail=f"{e}\n--- TRACE ---\n{tb}")


@router.get("/ucs/debug")
def ucs_debug() -> Dict[str, Any]:
    """Snapshot of UCS runtime (containers, active, atoms, addresses, etc.)."""
    try:
        return ucs_runtime.debug_snapshot()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"debug_snapshot failed: {e}")


# ----------------------------
# Route Planning
# ----------------------------
class ChooseRouteBody(BaseModel):
    goal: Dict[str, Any]
    k: int = 3


@router.post("/ucs/choose-route")
def ucs_choose_route(body: ChooseRouteBody) -> Dict[str, Any]:
    """
    Choose a route of atoms for a goal.

    Example:
      {
        "goal": {"caps": ["lean.replay"], "nodes": ["maxwell_eqs"]},
        "k": 3
      }
    """
    try:
        return ucs_runtime.choose_route(body.goal, k=body.k)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))