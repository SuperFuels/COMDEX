from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.aion.runtime.services.local_llm_service import LocalLLMService


router = APIRouter(
    prefix="/api/aion/local-llm",
    tags=["aion-local-llm"],
)


class LocalLLMGenerateRequest(BaseModel):
    prompt: str
    system: str | None = None


@router.get("/health")
def local_llm_health():
    service = LocalLLMService()
    return service.health()


@router.post("/generate")
def local_llm_generate(request: LocalLLMGenerateRequest):
    service = LocalLLMService()

    if not service.is_available():
        raise HTTPException(status_code=503, detail="Local LLM is not available")

    try:
        response = service.generate(
            prompt=request.prompt,
            system=request.system,
        )
        return {
            "ok": True,
            "response": response,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc