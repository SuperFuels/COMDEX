from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VoiceWorkerResult:
    ok: bool
    payload: dict[str, Any]
    stdout: str = ""
    stderr: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_voice_python() -> Path:
    root = repo_root()

    env_python = os.environ.get("AION_VOICE_PYTHON")
    if env_python:
        return Path(env_python)

    bundled = root / "desktop" / "mac" / "Tessaris.app" / "Contents" / "Resources" / "voice" / "python" / "bin" / "python"
    if bundled.exists():
        return bundled

    local = root / ".venv_voice" / "bin" / "python"
    if local.exists():
        return local

    return Path(sys.executable)


def voice_worker_script() -> Path:
    return repo_root() / "scripts" / "aion_voice_worker.py"


def call_voice_worker(mode: str, request: dict[str, Any], timeout: int = 120) -> VoiceWorkerResult:
    python_path = default_voice_python()
    worker_path = voice_worker_script()

    if not worker_path.exists():
        return VoiceWorkerResult(
            ok=False,
            payload={
                "ok": False,
                "stage": "worker_missing",
                "error": f"Voice worker script missing: {worker_path}",
            },
        )

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        request_path = Path(tmp.name)
        json.dump(request, tmp)

    try:
        proc = subprocess.run(
            [str(python_path), str(worker_path), mode, "--request", str(request_path)],
            cwd=str(repo_root()),
            text=True,
            capture_output=True,
            timeout=timeout,
        )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        try:
            payload = json.loads(stdout)
        except Exception:
            payload = {
                "ok": False,
                "stage": "worker_output",
                "error": "Voice worker did not return JSON.",
                "stdout": stdout[-4000:],
                "stderr": stderr[-4000:],
                "returncode": proc.returncode,
            }

        ok = bool(payload.get("ok")) and proc.returncode == 0
        if not ok:
            payload.setdefault("ok", False)
            payload.setdefault("returncode", proc.returncode)
            if stderr:
                payload.setdefault("stderr", stderr[-4000:])

        return VoiceWorkerResult(
            ok=ok,
            payload=payload,
            stdout=stdout,
            stderr=stderr,
        )

    except Exception as exc:
        return VoiceWorkerResult(
            ok=False,
            payload={
                "ok": False,
                "stage": "worker_call",
                "error": repr(exc),
            },
        )
    finally:
        try:
            request_path.unlink()
        except Exception:
            pass


def synthesize_with_worker(text: str, voice: str = "af_heart", sample_rate: int = 24000) -> VoiceWorkerResult:
    return call_voice_worker(
        "tts",
        {
            "text": text,
            "voice": voice,
            "sample_rate": sample_rate,
            "business_context_hardcoded": False,
        },
    )


def transcribe_with_worker(audio_bytes: bytes, filename: str = "audio.wav") -> VoiceWorkerResult:
    return call_voice_worker(
        "stt",
        {
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "filename": filename,
            "model": os.environ.get("AION_WHISPER_MODEL", "base"),
            "device": os.environ.get("AION_WHISPER_DEVICE", "auto"),
            "compute_type": os.environ.get("AION_WHISPER_COMPUTE_TYPE", "int8"),
            "business_context_hardcoded": False,
        },
    )
