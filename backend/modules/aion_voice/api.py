from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, File, UploadFile, Response
from fastapi.responses import JSONResponse

from backend.modules.aion_voice.providers.faster_whisper_stt import transcribe_audio_bytes
from backend.modules.aion_voice.voice_router import get_voice_provider_status, synthesize_text


router = APIRouter(prefix="/api/aion/voice", tags=["aion-voice"])


@router.get("/providers")
def aion_voice_provider_status() -> Dict[str, Any]:
    return get_voice_provider_status()


@router.post("/tts")
async def aion_voice_tts_router(payload: Dict[str, Any]) -> Response:
    result = synthesize_text(
        text=str(payload.get("text") or ""),
        provider=payload.get("provider"),
        voice_id=payload.get("voice_id"),
        model_id=payload.get("model_id"),
    )

    if result.ok and result.audio_bytes:
        return Response(
            content=result.audio_bytes,
            media_type=result.media_type,
            headers=result.headers,
        )

    return JSONResponse(
        status_code=200,
        content=result.to_json(),
        headers=result.headers,
    )


@router.post("/api/aion/voice/stt")
async def aion_voice_stt(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    result = transcribe_audio_bytes(audio_bytes, filename=file.filename or "audio.webm")
    return result.to_dict()

