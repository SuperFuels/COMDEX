from fastapi import APIRouter, Request
from pydantic import BaseModel
from backend.modules.glyphos.codexlang_translator import run_codexlang_string

router = APIRouter()

class PlaygroundInput(BaseModel):
    code: str
    container: str = "codex_playground.dc.json"
    source: str = "manual"

@router.post("/aion/codex-playground")
async def execute_codexlang(payload: PlaygroundInput, request: Request):
    try:
        result = run_codexlang_string(payload.code, context={"container": payload.container, "source": payload.source})
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }