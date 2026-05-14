# backend/api/media_api.py
from __future__ import annotations

import base64
import logging
import os
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/media", tags=["Media"])

# ── auth helpers (mirror glyphnet_router)
def _extract_token(request: Request, payload: Dict[str, Any]) -> Optional[str]:
    token = payload.get("token")
    if not token:
        token = request.headers.get("x-agent-token") or request.headers.get("X-Agent-Token")
    if not token:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
    return token

def _dev_token_allows(token: Optional[str]) -> bool:
    return os.getenv("GLYPHNET_ALLOW_DEV_TOKEN", "0").lower() in {"1", "true", "yes", "on"} and token in {"dev-token", "local-dev"}

# ── lazy load a transcription engine (optional)
_engine = None
_engine_name = None

def _lazy_engine():
    global _engine, _engine_name
    if _engine is not None:
        return _engine, _engine_name

    # Try faster-whisper first
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model_size = os.getenv("TRANSCRIBE_MODEL", "tiny")
        _engine = WhisperModel(model_size, compute_type=os.getenv("TRANSCRIBE_COMPUTE", "int8"))
        _engine_name = "faster-whisper"
        logger.info("[transcribe] using faster-whisper (%s)", model_size)
        return _engine, _engine_name
    except Exception:
        pass

    # Fallback to openai-whisper
    try:
        import whisper  # type: ignore
        model_size = os.getenv("TRANSCRIBE_MODEL", "tiny")
        _engine = whisper.load_model(model_size)
        _engine_name = "openai-whisper"
        logger.info("[transcribe] using openai-whisper (%s)", model_size)
        return _engine, _engine_name
    except Exception:
        pass

    _engine = None
    _engine_name = "stub"
    logger.warning("[transcribe] no engine available; returning empty text")
    return _engine, _engine_name

def _decode_b64_audio(b64: str) -> bytes:
    try:
        return base64.b64decode(b64, validate=True)
    except Exception:
        # tolerate data URLs
        if "," in b64 and b64.strip().lower().startswith("data:"):
            return base64.b64decode(b64.split(",", 1)[1], validate=False)
        raise

@router.post("/transcribe")
async def transcribe_audio(payload: Dict[str, Any], request: Request):
    """
    Body: { mime: string, data_b64: string }
    Returns: { text: string, engine: 'faster-whisper'|'openai-whisper'|'stub' }
    """
    token = _extract_token(request, payload)
    if not _dev_token_allows(token):
        raise HTTPException(status_code=401, detail="Unauthorized (enable GLYPHNET_ALLOW_DEV_TOKEN or pass a valid token)")

    mime = str(payload.get("mime") or "")
    data_b64 = payload.get("data_b64") or payload.get("bytes_b64") or ""
    if not data_b64:
        raise HTTPException(status_code=400, detail="missing data_b64")

    raw = _decode_b64_audio(data_b64)
    engine, which = _lazy_engine()

    # faster-whisper
    if which == "faster-whisper" and engine is not None:
        try:
            import tempfile, os as _os
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                tf.write(raw)
                tmp_path = tf.name
            try:
                segments, _info = engine.transcribe(tmp_path, vad_filter=True)
                text = " ".join(s.text.strip() for s in segments if s.text)
            finally:
                try: _os.remove(tmp_path)
                except Exception: pass
            return {"text": text.strip(), "engine": which}
        except Exception as e:
            logger.error("[transcribe] faster-whisper failed: %s", e)

    # openai-whisper
    if which == "openai-whisper" and engine is not None:
        try:
            import tempfile, os as _os
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                tf.write(raw)
                tmp_path = tf.name
            try:
                result = engine.transcribe(tmp_path, fp16=False)
                text = (result or {}).get("text") or ""
            finally:
                try: _os.remove(tmp_path)
                except Exception: pass
            return {"text": (text or "").strip(), "engine": which}
        except Exception as e:
            logger.error("[transcribe] whisper failed: %s", e)

    # stub fallback
    return {"text": "", "engine": "stub"}