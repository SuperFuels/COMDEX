# ============================================================
# 🧩 SCI Workspace Reinjection API
# ============================================================
"""
Reinjects a saved Photon state or scroll (.ptn) into the active workspace
and propagates it to SCI runtime + QFC visual layer.
"""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
import json
import logging

from backend.modules.sci_runtime.workspace import update_active_workspace
from backend.modules.qfc.qfc_broadcast import broadcast_qfc_event, trigger_qfc_render

router = APIRouter(prefix="/api/sci", tags=["SCI Reinjection"])

@router.post("/reinject_workspace")
async def reinject_workspace(request: Request):
    """
    Reinstate a saved Photon execution state into the active SCI/QFC environment.
    Payload example:
    {
        "container_id": "user:sci:active",
        "telemetry_path": "data/telemetry/scrolls/2025-10-29T22-17-11Z.ptn",
        "state": {...}  # optional inline state instead of path
    }
    """
    try:
        body = await request.json()
        container_id = body.get("container_id")
        telemetry_path = body.get("telemetry_path")
        state = body.get("state")

        if not container_id:
            raise HTTPException(status_code=400, detail="container_id is required")

        if not state and not telemetry_path:
            raise HTTPException(status_code=400, detail="Either state or telemetry_path must be provided")

        # Load telemetry if path provided
        if telemetry_path and not state:
            try:
                with open(telemetry_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to load telemetry: {e}")

        # Update active workspace
        await update_active_workspace(container_id, state)

        # Broadcast to QFC visualization layer
        await broadcast_qfc_event({
            "type": "workspace_reinjected",
            "container_id": container_id,
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "state": state,
        })
        await trigger_qfc_render({
            "type": "workspace_sync",
            "container_id": container_id,
            "frame": state,
        }, source="sci_reinject")

        logging.info(f"[SCI Reinjection] ✅ Workspace rehydrated → {container_id}")
        return {"ok": True, "container_id": container_id, "telemetry_path": telemetry_path}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[SCI Reinjection] ❌ Failed to reinject workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))