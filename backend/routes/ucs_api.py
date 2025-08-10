from fastapi import APIRouter, HTTPException
from typing import Dict, Any

# Make sure this is THE place where your ucs_runtime lives:
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime

# SQI bridge shims
from backend.modules.sqi.sqi_tessaris_bridge import (
    choose_route as sqi_choose_route,
    execute_route as sqi_execute_route,
)

router = APIRouter(prefix="/ucs", tags=["UCS"])

@router.get("/debug")
def ucs_debug():
    # expose a compact debug state; add debug_state() on ucs_runtime if missing
    if hasattr(ucs_runtime, "debug_state"):
        return ucs_runtime.debug_state()
    # fallback if you haven't added debug_state yet
    return {
        "containers_loaded": list(getattr(ucs_runtime, "container_index", {}).keys()),
        "atom_index": list(getattr(ucs_runtime, "atom_index", {}).keys()),
    }

@router.post("/route")
def ucs_route(goal: Dict[str, Any]):
    try:
        plan = sqi_choose_route(goal)
        if not plan.get("atoms"):
            raise HTTPException(status_code=404, detail="No atoms matched the goal.")
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
def ucs_execute(payload: Dict[str, Any]):
    plan = payload.get("plan")
    ctx  = payload.get("ctx", {})
    if not plan:
        raise HTTPException(status_code=400, detail="Missing 'plan' in body.")
    try:
        result = sqi_execute_route(plan, ctx)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))