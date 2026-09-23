from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from backend.modules.aion_voice.voice_download_policy import build_voice_download_policy_env
from typing import Any


@dataclass(frozen=True)
class VoiceWorkerResult:
    ok: bool
    payload: dict[str, Any]
    stdout: str = ""
    stderr: str = ""


# One local process retains both Kokoro and Whisper models after their first use.
# Requests are serialised because both models share the same private runtime.
_PERSISTENT_TTS_PROCESS: subprocess.Popen[str] | None = None
_PERSISTENT_TTS_LOCK = threading.Lock()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]



AION_O23F_PACKAGED_VOICE_RESOLVER_VERSION = "aion.voice.o23f.packaged_resolver.v1"


def voice_bundle_staging_root() -> Path:
    return repo_root() / "desktop" / "mac" / "voice_bundle_staging" / "voice"


def voice_bundle_packaged_root() -> Path:
    return (
        repo_root()
        / "desktop"
        / "mac"
        / "Tessaris.app"
        / "Contents"
        / "Resources"
        / "voice"
    )


def voice_bundle_root_from_env() -> Path | None:
    raw = os.environ.get("AION_VOICE_BUNDLE_ROOT", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def voice_python_for_bundle_root(bundle_root: Path) -> Path:
    return bundle_root / "python" / "bin" / "python"


def resolve_voice_bundle_root() -> Path:
    override = voice_bundle_root_from_env()
    if override is not None:
        return override

    mode = os.environ.get("AION_VOICE_RUNTIME_MODE", "").strip().lower()

    if mode in {"packaged", "app", "bundle"}:
        return voice_bundle_packaged_root()

    if mode in {"staging", "bundle_staging", "staged"}:
        return voice_bundle_staging_root()

    staging = voice_bundle_staging_root()
    if voice_python_for_bundle_root(staging).exists():
        return staging

    packaged = voice_bundle_packaged_root()
    if voice_python_for_bundle_root(packaged).exists():
        return packaged

    return staging


def resolve_voice_python() -> Path:
    explicit = os.environ.get("AION_VOICE_PYTHON", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    bundle_python = voice_python_for_bundle_root(resolve_voice_bundle_root())
    if bundle_python.exists():
        return bundle_python

    development = repo_root() / ".venv_voice" / "bin" / "python"
    if development.exists():
        return development

    legacy_packaged = (
        repo_root()
        / "desktop"
        / "mac"
        / "Tessaris.app"
        / "Contents"
        / "Resources"
        / "voice"
        / "python"
        / "bin"
        / "python"
    )
    if legacy_packaged.exists():
        return legacy_packaged

    return Path(sys.executable)


def default_voice_python() -> Path:
    return resolve_voice_python()

def voice_worker_script() -> Path:
    return repo_root() / "scripts" / "aion_voice_worker.py"



def voice_worker_environment() -> dict[str, str]:
    env = build_voice_download_policy_env(os.environ)
    bundle_root = resolve_voice_bundle_root()

    env.setdefault("AION_VOICE_BUNDLE_ROOT", str(bundle_root))
    env.setdefault("AION_KOKORO_MODEL_PATH", str(bundle_root / "kokoro" / "kokoro-v1_0.pth"))
    env.setdefault("AION_KOKORO_CONFIG_PATH", str(bundle_root / "kokoro" / "config.json"))
    env.setdefault("AION_KOKORO_VOICE_PATH", str(bundle_root / "kokoro" / "voices" / "af_heart.pt"))
    env.setdefault("AION_SPACY_MODEL_PATH", str(bundle_root / "spacy" / "en_core_web_sm"))
    env.setdefault("AION_WHISPER_MODEL_PATH", str(bundle_root / "whisper" / "base"))

    return env


def _write_worker_request(mode: str, request: dict[str, Any]) -> Path:
    import tempfile
    import uuid

    # The worker CLI receives mode as argv and reads this JSON from --request.
    # Keep operation fields such as text, voice and sample_rate at the top level.
    payload = dict(request or {})
    payload.setdefault("mode", str(mode))
    payload.setdefault("operation", str(mode))

    request_path = Path(tempfile.gettempdir()) / f"aion_voice_worker_request_{uuid.uuid4().hex}.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    return request_path

def call_voice_worker(
    mode: str,
    request: dict[str, Any],
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> VoiceWorkerResult:
    if mode in {"tts", "stt"}:
        return _call_persistent_voice_worker(mode=mode, request=request, env=env)

    python_path = resolve_voice_python()
    try:
        worker_path = resolve_voice_worker_script()
    except NameError:
        worker_path = voice_worker_script()
    try:
        runtime_root = resolve_voice_runtime_root()
    except NameError:
        try:
            runtime_root = voice_runtime_root()
        except NameError:
            runtime_root = worker_path.parent
    merged_env = voice_worker_environment()
    if env:
        merged_env.update({str(key): str(value) for key, value in env.items()})

    request_path = _write_worker_request(mode=mode, request=request)

    try:
        completed = subprocess.run(
            [str(python_path), str(worker_path), str(mode), "--request", str(request_path)],
            cwd=str(runtime_root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=merged_env,
            check=False,
        )

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()

        try:
            payload = json.loads(stdout) if stdout else {}
        except Exception:
            payload = {
                "ok": False,
                "error": "Voice worker returned non-JSON stdout.",
                "stdout": stdout[-4000:],
                "stderr": stderr[-4000:],
            }

        if completed.returncode != 0:
            payload.setdefault("ok", False)
            payload.setdefault("error", f"Voice worker exited with code {completed.returncode}.")
            payload.setdefault("stderr", stderr[-4000:])

        payload.setdefault("returncode", int(completed.returncode))
        payload.setdefault("python_path", str(python_path))
        payload.setdefault("worker_path", str(worker_path))
        payload.setdefault("runtime_root", str(runtime_root))

        return VoiceWorkerResult(
            ok=bool(payload.get("ok")),
            payload=payload,
            stdout=stdout,
            stderr=stderr,
        )
    finally:
        try:
            request_path.unlink()
        except Exception:
            pass


def _start_persistent_tts_worker(env: dict[str, str] | None = None) -> subprocess.Popen[str]:
    global _PERSISTENT_TTS_PROCESS

    if _PERSISTENT_TTS_PROCESS is not None and _PERSISTENT_TTS_PROCESS.poll() is None:
        return _PERSISTENT_TTS_PROCESS

    python_path = resolve_voice_python()
    try:
        worker_path = resolve_voice_worker_script()
    except NameError:
        worker_path = voice_worker_script()
    try:
        runtime_root = resolve_voice_runtime_root()
    except NameError:
        try:
            runtime_root = voice_runtime_root()
        except NameError:
            runtime_root = worker_path.parent

    merged_env = voice_worker_environment()
    if env:
        merged_env.update({str(key): str(value) for key, value in env.items()})

    _PERSISTENT_TTS_PROCESS = subprocess.Popen(
        [str(python_path), str(worker_path), "serve"],
        cwd=str(runtime_root),
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=1,
        env=merged_env,
    )
    return _PERSISTENT_TTS_PROCESS


def _call_persistent_voice_worker(
    mode: str,
    request: dict[str, Any],
    env: dict[str, str] | None = None,
) -> VoiceWorkerResult:
    global _PERSISTENT_TTS_PROCESS
    payload_request = dict(request or {})
    payload_request.setdefault("mode", mode)
    payload_request.setdefault("operation", mode)

    with _PERSISTENT_TTS_LOCK:
        for attempt in range(2):
            process = _start_persistent_tts_worker(env=env)
            try:
                if process.stdin is None or process.stdout is None:
                    raise RuntimeError("Persistent voice worker pipes are unavailable")
                process.stdin.write(json.dumps(payload_request, separators=(",", ":")) + "\n")
                process.stdin.flush()
                response_line = process.stdout.readline()
                if not response_line:
                    raise RuntimeError("Persistent voice worker stopped without a response")
                payload = json.loads(response_line)
                payload.setdefault("persistent_worker", True)
                payload.setdefault("worker_pid", process.pid)
                return VoiceWorkerResult(ok=bool(payload.get("ok")), payload=payload)
            except Exception as exc:
                try:
                    process.kill()
                except Exception:
                    pass
                _PERSISTENT_TTS_PROCESS = None
                if attempt == 1:
                    payload = {
                        "ok": False,
                        "stage": "persistent_worker",
                        "error": repr(exc),
                        "persistent_worker": True,
                    }
                    return VoiceWorkerResult(ok=False, payload=payload)

    return VoiceWorkerResult(ok=False, payload={"ok": False, "error": "Persistent worker unavailable"})


def _call_persistent_tts_worker(
    request: dict[str, Any],
    env: dict[str, str] | None = None,
) -> VoiceWorkerResult:
    return _call_persistent_voice_worker("tts", request=request, env=env)


def synthesize_with_worker(text: str, voice: str = "af_heart", sample_rate: int = 24000) -> VoiceWorkerResult:
    return call_voice_worker(
        "tts",
        {
            "text": text,
            "voice": voice,
            "sample_rate": sample_rate,
            "business_context_hardcoded": False,
        },
        env=voice_worker_environment()
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
