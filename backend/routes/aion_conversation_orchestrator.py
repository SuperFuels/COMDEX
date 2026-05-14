from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.modules.aion_conversation.conversation_orchestrator import ConversationOrchestrator

router = APIRouter()
_ORCH = ConversationOrchestrator()


class ConversationTurnRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1)
    user_text: str = Field(..., min_length=1)
    apply_teaching: Optional[bool] = None
    include_metadata: bool = True
    include_debug: bool = False


class ConversationStateRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1)


@router.post("/conversation/turn")
async def conversation_turn(payload: ConversationTurnRequest) -> Dict[str, Any]:
    return _ORCH.handle_turn(
        session_id=payload.session_id,
        user_text=payload.user_text,
        apply_teaching=payload.apply_teaching,
        include_debug=payload.include_debug,
        include_metadata=payload.include_metadata,
    )


@router.get("/conversation/state")
async def conversation_state(session_id: str = "default") -> Dict[str, Any]:
    return {
        "ok": True,
        "origin": "aion_conversation_orchestrator",
        "state": _ORCH.get_state(session_id),
    }


@router.post("/conversation/reset")
async def conversation_reset(payload: ConversationStateRequest) -> Dict[str, Any]:
    return _ORCH.reset_state(payload.session_id)