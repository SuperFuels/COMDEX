from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "desktop/mac/src/app.js"
API_PATH = ROOT / "backend/modules/aion_voice/api.py"
OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o22f"
OUT_PATH = OUT_DIR / "frontend_mic_contract_manifest.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    app = APP_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")

    checks = {
        "frontend_has_stt_endpoint": '"/api/aion/voice/stt"' in app,
        "frontend_has_media_recorder": "MediaRecorder" in app,
        "frontend_has_get_user_media": "getUserMedia" in app,
        "frontend_posts_audio_chunk": "postAionO21EAudioChunkToStt" in app and "FormData" in app,
        "frontend_appends_transcript": "appendAionO21ETranscript" in app,
        "frontend_no_browser_speech_fallback_flag": "no_browser_speech_fallback" in app,
        "frontend_no_elevenlabs_flag": "no_elevenlabs_call" in app,
        "backend_has_stt_route": '@router.post("/stt")' in api,
        "backend_has_worker_gate": "AION_VOICE_WORKER_ENABLED" in api,
        "backend_uses_worker_transcribe": "transcribe_with_worker" in api,
        "backend_returns_worker_header": "x-aion-voice-worker" in api,
        "backend_blocks_cloud_header": "x-aion-voice-cloud" in api,
    }

    for key, value in checks.items():
        require(value, f"Failed O22F check: {key}")

    forbidden_app_tokens = [
        "new SpeechRecognition(",
        "new webkitSpeechRecognition(",
        "SpeechRecognition()",
        "webkitSpeechRecognition()",
        "api.elevenlabs.io",
        "elevenlabs.io",
    ]

    forbidden_hits = [token for token in forbidden_app_tokens if token in app]
    require(not forbidden_hits, f"Forbidden frontend voice calls found: {forbidden_hits}")

    manifest = {
        "ok": True,
        "phase": "O22F",
        "goal": "frontend_mic_posts_to_backend_worker_stt",
        "frontend_file": str(APP_PATH.relative_to(ROOT)),
        "backend_file": str(API_PATH.relative_to(ROOT)),
        "stt_endpoint": "/api/aion/voice/stt",
        "worker_gate": "AION_VOICE_WORKER_ENABLED=true",
        "checks": checks,
        "browser_speech_runtime_call_allowed": False,
        "elevenlabs_runtime_call_allowed": False,
        "business_context_hardcoded": False,
    }

    OUT_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
