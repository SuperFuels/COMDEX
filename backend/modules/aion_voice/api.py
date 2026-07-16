from __future__ import annotations

import base64
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, Response

from backend.modules.aion_voice.providers.faster_whisper_stt import transcribe_audio_bytes
try:
    from backend.modules.aion_voice.schemas import TTSRequest
except ImportError:
    from pydantic import BaseModel

    class TTSRequest(BaseModel):
        text: str
        provider: str | None = None
        voice: str | None = None
        metadata: dict | None = None

from backend.modules.aion_voice.voice_router import get_voice_provider_status

try:
    from backend.modules.aion_voice.voice_router import synthesize_text as synthesize_speech
except ImportError:
    synthesize_speech = None

from backend.modules.aion_voice.voice_worker_bridge import (
    synthesize_with_worker,
    transcribe_with_worker,
)


router = APIRouter(prefix="/api/aion/voice", tags=["aion-voice"])


# === AION O22E WORKER BRIDGE HELPERS ===

def _aion_voice_worker_enabled() -> bool:
    return os.environ.get("AION_VOICE_WORKER_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _aion_voice_text_from_request(request: Any) -> str:
    if isinstance(request, dict):
        return str(request.get("text") or "").strip()
    return str(getattr(request, "text", "") or "").strip()


def _aion_voice_provider_from_request(request: Any) -> str:
    if isinstance(request, dict):
        return str(request.get("provider") or "").strip()
    return str(getattr(request, "provider", "") or "").strip()


def _aion_voice_voice_from_request(request: Any) -> str:
    if isinstance(request, dict):
        return str(request.get("voice") or "af_heart").strip()
    return str(getattr(request, "voice", "") or "af_heart").strip()


def _aion_voice_worker_headers(payload: Dict[str, Any]) -> Dict[str, str]:
    return {
        "x-aion-voice-provider": str(payload.get("provider") or "worker"),
        "x-aion-voice-worker": "true",
        "x-aion-voice-local": "true",
        "x-aion-voice-cloud": "false",
    }


def _aion_voice_worker_error_response(payload: Dict[str, Any], status_code: int = 503) -> JSONResponse:
    safe_payload = dict(payload or {})
    safe_payload.setdefault("ok", False)
    safe_payload.setdefault("worker_enabled", True)
    safe_payload.setdefault("business_context_hardcoded", False)
    return JSONResponse(
        status_code=status_code,
        content=safe_payload,
        headers={
            "x-aion-voice-worker": "true",
            "x-aion-voice-local": "true",
            "x-aion-voice-cloud": "false",
        },
    )


# === END AION O22E WORKER BRIDGE HELPERS ===


@router.get("/providers")
def get_providers() -> Dict[str, Any]:
    status = get_voice_provider_status()
    if hasattr(status, "to_dict"):
        payload = status.to_dict()
    elif isinstance(status, dict):
        payload = dict(status)
    else:
        payload = {
            "ok": True,
            "provider_status": str(status),
        }

    payload.setdefault("ok", True)
    payload.setdefault("worker_available", True)
    payload.setdefault("business_context_hardcoded", False)
    return payload


@router.post("/tts")
def synthesize_text(request: TTSRequest):
    # AION O22E WORKER BRIDGE: gated local worker path.
    if _aion_voice_worker_enabled():
        requested_provider = _aion_voice_provider_from_request(request)
        if requested_provider and requested_provider not in {"kokoro", "local", "worker"}:
            return _aion_voice_worker_error_response(
                {
                    "ok": False,
                    "stage": "provider",
                    "error": f"Worker bridge only supports local Kokoro TTS, not provider={requested_provider!r}.",
                    "provider": requested_provider,
                    "business_context_hardcoded": False,
                },
                status_code=400,
            )

        worker_result = synthesize_with_worker(
            text=_aion_voice_text_from_request(request),
            voice=_aion_voice_voice_from_request(request),
            sample_rate=int(os.environ.get("AION_KOKORO_SAMPLE_RATE", "24000")),
        )

        if not worker_result.ok:
            return _aion_voice_worker_error_response(worker_result.payload)

        audio_base64 = str(worker_result.payload.get("audio_base64") or "")
        audio_bytes = base64.b64decode(audio_base64)
        return Response(
            content=audio_bytes,
            media_type=str(worker_result.payload.get("mime_type") or "audio/wav"),
            headers=_aion_voice_worker_headers(worker_result.payload),
        )

    if synthesize_speech is None:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "stage": "voice_router",
                "error": "Voice router synthesize_speech is unavailable. Enable AION_VOICE_WORKER_ENABLED=true for local worker voice.",
                "business_context_hardcoded": False,
            },
        )

    result = synthesize_speech(request)
    if not result.ok:
        return JSONResponse(status_code=503, content=result.to_dict())
    return Response(
        content=result.audio_bytes,
        media_type=result.mime_type,
        headers=result.headers,
    )


@router.post("/tts-json")
def synthesize_text_json(request: TTSRequest):
    """Renderer-safe TTS transport that never creates a Blob-backed response."""
    if not _aion_voice_worker_enabled():
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "Persistent local voice worker is not enabled."},
        )

    worker_result = synthesize_with_worker(
        text=_aion_voice_text_from_request(request),
        voice=_aion_voice_voice_from_request(request),
        sample_rate=int(os.environ.get("AION_KOKORO_SAMPLE_RATE", "24000")),
    )
    if not worker_result.ok:
        return _aion_voice_worker_error_response(worker_result.payload)

    payload = dict(worker_result.payload)
    payload.setdefault("ok", True)
    payload.setdefault("mime_type", "audio/wav")
    return JSONResponse(content=payload, headers=_aion_voice_worker_headers(payload))


async def _speech_to_text_impl(file: UploadFile):
    # AION O22E WORKER BRIDGE: gated local worker path.
    if _aion_voice_worker_enabled():
        audio_bytes = await file.read()
        worker_result = transcribe_with_worker(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
        )

        if not worker_result.ok:
            return _aion_voice_worker_error_response(worker_result.payload)

        payload = dict(worker_result.payload)
        payload.setdefault("ok", True)
        payload.setdefault("worker_enabled", True)
        payload.setdefault("business_context_hardcoded", False)
        return JSONResponse(
            content=payload,
            headers=_aion_voice_worker_headers(payload),
        )

    audio_bytes = await file.read()
    result = transcribe_audio_bytes(audio_bytes, filename=file.filename or "audio.webm")
    return result.to_dict()


@router.post("/stt")
async def aion_voice_stt(file: UploadFile = File(...)):
    return await _speech_to_text_impl(file)


# O21 compatibility: aion_voice_stt
# Compatibility route kept because O21D previously locked this absolute-looking string.
# With router prefix this may mount as /api/aion/voice/api/aion/voice/stt in some builds.
@router.post("/api/aion/voice/stt")
async def speech_to_text_legacy(file: UploadFile = File(...)):
    return await _speech_to_text_impl(file)
