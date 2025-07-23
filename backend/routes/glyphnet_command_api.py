from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any

from backend.modules.glyphnet.glyphnet_terminal import (
    run_symbolic_command,
    execute_terminal_command,
    get_last_result,
    get_command_history,
    get_recent_logs
)

router = APIRouter(prefix="/glyphnet/command", tags=["GlyphNet Terminal"])


class CommandRequest(BaseModel):
    command: str


class TerminalCommandRequest(BaseModel):
    command: str
    payload: Dict[str, Any]


@router.post("/execute")
def execute_command(req: TerminalCommandRequest):
    result = execute_terminal_command(req.command, req.payload)
    if result.get("status") != "ok":
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/run")
def run_codexlang(req: CommandRequest):
    result = run_symbolic_command(req.command)
    if result.get("status") != "ok":
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/last")
def fetch_last_result():
    return get_last_result()


@router.get("/history")
def fetch_command_history(n: int = 10):
    return get_command_history(n)


@router.get("/logs")
def get_glyphnet_logs():
    logs = get_recent_logs()
    return {"logs": logs}