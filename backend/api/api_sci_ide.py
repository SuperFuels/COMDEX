# ============================================================
#  🧠 SCI IDE API - PhotonLang Execution & Tab Management
# ============================================================
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, List, Optional
import asyncio
import json
import time

# Internal modules
from backend.modules.sci.sci_core import SCIRuntimeGateway
from backend.modules.sci.sci_replay_injector import SCIReplayInjector
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

router = APIRouter(prefix="/api/sci", tags=["sci_ide"])

# Global singletons
RMC = ResonantMemoryCache()
RUNTIME = SCIRuntimeGateway(container_id="sci_ide_runtime")
REPLAY = SCIReplayInjector()


# ============================================================
#  /api/sci/run - Execute PhotonLang or SCI source
# ============================================================
@router.post("/run")
async def sci_run(request: Request):
    """
    Execute a PhotonLang or SCI script block and broadcast results to QFC.
    Expects JSON: { "code": "...", "container_id": "...", "user_id": "..." }
    """
    body = await request.json()
    code: str = body.get("code", "")
    container_id: Optional[str] = body.get("container_id")
    user_id: Optional[str] = body.get("user_id", "default")

    if not code.strip():
        return JSONResponse({"ok": False, "error": "Empty source code."})

    try:
        # Execute PhotonLang code inside SCI runtime
        result = await RUNTIME.execute_photon_code(code, container_id=container_id, user_id=user_id)

        # Persist result snapshot to Resonant Memory
        scroll_label = f"run_{int(time.time())}"
        RMC.add_entry(
            label=scroll_label,
            state=result,
            metadata={"source": "sci_run", "user_id": user_id, "container_id": container_id},
        )

        # Optional broadcast into live QFC field
        asyncio.create_task(REPLAY._async_qfc_broadcast(result, container_id, user_id))

        return JSONResponse({"ok": True, "result": result, "label": scroll_label})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


# ============================================================
#  /api/sci/tabs - List or persist IDE tab metadata
# ============================================================
@router.get("/tabs")
async def list_sci_tabs():
    """
    Returns a snapshot of available IDE panels for the frontend.
    Enables remote persistence / synchronization with the IDE state.
    """
    try:
        tabs = [
            {"id": "atomsheet", "title": "AtomSheet"},
            {"id": "sqs", "title": "SQS"},
            {"id": "goals", "title": "Goals"},
            {"id": "memory", "title": "Memory Scrolls"},
        ]
        return JSONResponse({"ok": True, "tabs": tabs})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


@router.post("/tabs")
async def save_sci_tabs(request: Request):
    """
    Saves current IDE tab layout (optional, future persistence).
    Body: { "tabs": [...] }
    """
    body = await request.json()
    tabs = body.get("tabs", [])
    RMC.add_entry(label="tabs_state", state={"tabs": tabs})
    return JSONResponse({"ok": True, "count": len(tabs)})