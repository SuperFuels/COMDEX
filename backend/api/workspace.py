# backend/api/workspace.py
from __future__ import annotations

from typing import Any, Dict, Optional, Literal
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.modules.workspace.workspace_bridge import submit_workspace_query

# Expose this symbol for main.py
workspace_router = APIRouter(prefix="/api/workspace", tags=["workspace"])


# --------- Schemas ---------
class WorkspaceQueryRequest(BaseModel):
    container_id: str = Field(..., description="Target container id")
    query_type: Literal["symbolic_query", "codexlang", "hypothesis"] = "symbolic_query"
    symbolic_tree: Optional[Dict[str, Any]] = Field(
        default=None, description="Symbolic structure or hypothesis tree"
    )
    reason: Optional[str] = Field(default=None, description="Audit reason or source")
    carrier_type: Optional[str] = Field(default="simulated", description="Beam style")


class WorkspaceQueryResponse(BaseModel):
    ok: bool
    wave_id: str
    scores: Dict[str, float]


# --------- HTTP endpoint ---------
@workspace_router.post("/submit", response_model=WorkspaceQueryResponse)
def submit(req: WorkspaceQueryRequest) -> WorkspaceQueryResponse:
    """
    Bridge a workspace query into the research engine and broadcast results
    (QWave + glyphwave events). Synchronous-friendly; spawns async where needed.
    """
    result = submit_workspace_query(
        container_id=req.container_id,
        query_type=req.query_type,
        symbolic_tree=req.symbolic_tree,
        reason=req.reason,
        carrier_type=req.carrier_type,
    )
    return WorkspaceQueryResponse(**result)


# --------- WebSocket endpoint ---------
@workspace_router.websocket("/ws")
async def workspace_ws(ws: WebSocket):
    """
    Minimal WS that accepts JSON messages matching WorkspaceQueryRequest,
    feeds them into the bridge, and returns a JSON ack with the result.
    """
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            # Basic validation via Pydantic
            req = WorkspaceQueryRequest(**data)

            # Run the sync bridge without blocking too long
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                submit_workspace_query,
                req.container_id,
                req.query_type,
                req.symbolic_tree,
                req.reason,
                req.carrier_type,
            )

            await ws.send_json({"type": "ack", "ok": True, "result": result})
    except WebSocketDisconnect:
        # client closed – nothing to do
        return
    except Exception as e:
        await ws.send_json({"type": "error", "ok": False, "message": str(e)})

@workspace_router.get("/health")
def health():
    return {"ok": True, "service": "workspace", "status": "ready"}