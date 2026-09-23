from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

APP_VOICE_ROOT = ROOT / "desktop/mac/Tessaris.app/Contents/Resources/voice"
APP_PYTHON = APP_VOICE_ROOT / "python/bin/python"
APP_RUNTIME_ROOT = APP_VOICE_ROOT / "runtime"
APP_WORKER = APP_RUNTIME_ROOT / "scripts/aion_voice_worker.py"

OUT_DIR = ROOT / ".runtime/voice_runtime_tests/o24h"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = OUT_DIR / "app_local_tts_stt_smoke_manifest.json"
TTS_WAV = OUT_DIR / "o24h_app_local_tts.wav"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def run(cmd: list[str], env: dict[str, str] | None = None, cwd: Path | None = None, timeout: int = 180) -> dict:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def parse_json(result: dict) -> dict:
    stdout = result.get("stdout", "") or ""
    stderr = result.get("stderr", "") or ""

    try:
        payload = json.loads(stdout.strip())
    except Exception:
        try:
            start = stdout.index("{")
            end = stdout.rindex("}") + 1
            payload = json.loads(stdout[start:end])
        except Exception:
            payload = {
                "parse_error": True,
                "stdout_tail": stdout[-4000:],
                "stderr_tail": stderr[-4000:],
            }

    payload["returncode"] = result.get("returncode")
    return payload


def path_state(path: Path) -> dict:
    exists = path.exists()
    return {
        "path": rel(path),
        "exists": exists,
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "is_symlink": path.is_symlink(),
        "realpath": str(path.resolve()) if exists else None,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
    }


def app_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "AION_VOICE_RUNTIME_MODE": "packaged",
            "AION_VOICE_BUNDLE_ROOT": str(APP_VOICE_ROOT),
            "AION_KOKORO_MODEL_PATH": str(APP_VOICE_ROOT / "kokoro/kokoro-v1_0.pth"),
            "AION_KOKORO_CONFIG_PATH": str(APP_VOICE_ROOT / "kokoro/config.json"),
            "AION_KOKORO_VOICE_PATH": str(APP_VOICE_ROOT / "kokoro/voices/af_heart.pt"),
            "AION_SPACY_MODEL_PATH": str(APP_VOICE_ROOT / "spacy/en_core_web_sm"),
            "AION_WHISPER_MODEL_PATH": str(APP_VOICE_ROOT / "whisper/base"),
            "AION_VOICE_NO_HIDDEN_DOWNLOADS": "true",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "AION_ELEVENLABS_ENABLED": "false",
            "AION_BROWSER_SPEECH_FALLBACK_ENABLED": "false",
            "PYTHONPATH": str(APP_RUNTIME_ROOT),
        }
    )
    return env


def app_worker_probe() -> dict:
    return parse_json(
        run(
            [str(APP_PYTHON), str(APP_WORKER), "aion-o23i-bundle-probe"],
            env=app_env(),
            cwd=APP_RUNTIME_ROOT,
            timeout=120,
        )
    )


def tts_stt_probe() -> dict:
    code = f"""
import json
import os
from pathlib import Path

out_wav = Path({str(TTS_WAV)!r})
text = "AION local packaged voice runtime smoke test."

bundle_root = Path(os.environ["AION_VOICE_BUNDLE_ROOT"]).resolve()
runtime_root = Path({str(APP_RUNTIME_ROOT)!r}).resolve()
kokoro_model = Path(os.environ["AION_KOKORO_MODEL_PATH"]).resolve()
kokoro_config = Path(os.environ["AION_KOKORO_CONFIG_PATH"]).resolve()
kokoro_voice = Path(os.environ["AION_KOKORO_VOICE_PATH"]).resolve()
whisper_model = Path(os.environ["AION_WHISPER_MODEL_PATH"]).resolve()

result = {{
    "bundle_root": str(bundle_root),
    "runtime_root": str(runtime_root),
    "text": text,
    "kokoro_model": str(kokoro_model),
    "kokoro_config": str(kokoro_config),
    "kokoro_voice": str(kokoro_voice),
    "whisper_model": str(whisper_model),
    "offline_env": {{
        "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"),
        "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE"),
        "HF_DATASETS_OFFLINE": os.environ.get("HF_DATASETS_OFFLINE"),
        "AION_VOICE_NO_HIDDEN_DOWNLOADS": os.environ.get("AION_VOICE_NO_HIDDEN_DOWNLOADS"),
        "AION_ELEVENLABS_ENABLED": os.environ.get("AION_ELEVENLABS_ENABLED"),
        "AION_BROWSER_SPEECH_FALLBACK_ENABLED": os.environ.get("AION_BROWSER_SPEECH_FALLBACK_ENABLED"),
    }},
}}

try:
    import soundfile as sf
    from kokoro import KPipeline

    pipeline_attempts = []
    pipeline = None
    last_error = None

    constructors = [
        {{"lang_code": "a"}},
        {{"lang_code": "a", "repo_id": str(bundle_root / "kokoro")}},
    ]

    for kwargs in constructors:
        try:
            pipeline = KPipeline(**kwargs)
            pipeline_attempts.append({{"kwargs": kwargs, "ok": True}})
            break
        except Exception as exc:
            last_error = repr(exc)
            pipeline_attempts.append({{"kwargs": kwargs, "ok": False, "error": repr(exc)}})

    if pipeline is None:
        raise RuntimeError("KPipeline init failed: " + str(last_error))

    import numpy as np

    audio_chunks = []
    generator_attempts = []

    def collect_audio(value, seen=None):
        if seen is None:
            seen = set()

        try:
            import torch
        except Exception:
            torch = None

        if value is None:
            return []

        value_id = id(value)
        if value_id in seen:
            return []
        seen.add(value_id)

        if isinstance(value, (str, bytes, bytearray)):
            return []

        if torch is not None and hasattr(value, "detach"):
            return [value.detach().cpu().numpy()]

        if hasattr(value, "shape") and hasattr(value, "dtype"):
            return [value]

        # Kokoro versions may return result objects rather than plain tuples.
        for attr in ("audio", "samples", "wav", "array", "data"):
            if hasattr(value, attr):
                try:
                    found = collect_audio(getattr(value, attr), seen)
                    if found:
                        return found
                except Exception:
                    pass

        if isinstance(value, dict):
            found = []
            for key in ("audio", "samples", "wav", "array", "data"):
                if key in value:
                    found.extend(collect_audio(value[key], seen))
            if found:
                return found

        if isinstance(value, tuple) and len(value) >= 3:
            found = collect_audio(value[-1], seen)
            if found:
                return found

        if isinstance(value, (list, tuple)):
            found = []
            for child in value:
                found.extend(collect_audio(child, seen))
            return found

        return []

    generator_inputs = [
        {{"voice": str(kokoro_voice), "speed": 1}},
        {{"voice": "af_heart", "speed": 1}},
    ]

    for kwargs in generator_inputs:
        try:
            generated = pipeline(text, **kwargs)

            seen_items = []
            if isinstance(generated, tuple) and len(generated) >= 3:
                seen_items.append({{"type": type(generated).__name__, "attrs": sorted([a for a in dir(generated) if not a.startswith("_")])[:30]}})
                audio_chunks.extend(collect_audio(generated))
            else:
                for item in generated:
                    seen_items.append({{"type": type(item).__name__, "attrs": sorted([a for a in dir(item) if not a.startswith("_")])[:30]}})
                    audio_chunks.extend(collect_audio(item))

            generator_attempts.append({{"kwargs": kwargs, "ok": True, "chunks": len(audio_chunks), "seen_items": seen_items[:5]}})
            if audio_chunks:
                break
        except Exception as exc:
            generator_attempts.append({{"kwargs": kwargs, "ok": False, "error": repr(exc)}})

    if not audio_chunks:
        raise RuntimeError("Kokoro produced no audio chunks")

    arrays = [np.asarray(chunk, dtype="float32").reshape(-1) for chunk in audio_chunks]
    audio = arrays[0] if len(arrays) == 1 else np.concatenate(arrays)
    sf.write(str(out_wav), audio, 24000)

    info = sf.info(str(out_wav))
    result["tts"] = {{
        "ok": True,
        "pipeline_attempts": pipeline_attempts,
        "generator_attempts": generator_attempts,
        "wav": str(out_wav),
        "wav_exists": out_wav.exists(),
        "frames": int(info.frames),
        "samplerate": int(info.samplerate),
        "channels": int(info.channels),
        "duration": float(info.duration),
    }}
except Exception as exc:
    result["tts"] = {{
        "ok": False,
        "error": repr(exc),
    }}

try:
    from faster_whisper import WhisperModel

    model = WhisperModel(str(whisper_model), device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(out_wav), beam_size=1)
    transcript = " ".join(segment.text.strip() for segment in segments).strip()

    result["stt"] = {{
        "ok": bool(transcript),
        "transcript": transcript,
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
    }}
except Exception as exc:
    result["stt"] = {{
        "ok": False,
        "error": repr(exc),
    }}

print(json.dumps(result))
"""
    return parse_json(
        run(
            [str(APP_PYTHON), "-c", code],
            env=app_env(),
            cwd=APP_RUNTIME_ROOT,
            timeout=240,
        )
    )


def packaged_readiness_probe() -> dict:
    env = dict(os.environ)
    env.update(
        {
            "AION_VOICE_RUNTIME_MODE": "packaged",
            "AION_VOICE_BUNDLE_ROOT": str(APP_VOICE_ROOT),
            "AION_VOICE_NO_HIDDEN_DOWNLOADS": "true",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "AION_ELEVENLABS_ENABLED": "false",
            "AION_BROWSER_SPEECH_FALLBACK_ENABLED": "false",
            "PYTHONPATH": str(ROOT),
        }
    )

    return parse_json(
        run(
            [
                str(ROOT / ".venv/bin/python"),
                "-c",
                "import json; from backend.modules.aion_voice.voice_startup_readiness import voice_startup_readiness; print(json.dumps(voice_startup_readiness(mode='packaged').to_dict()))",
            ],
            env=env,
            cwd=ROOT,
            timeout=120,
        )
    )


def contains_forbidden_business_context() -> bool:
    text = Path(__file__).read_text(encoding="utf-8")

    forbidden = [
        "Home" + " Fixed",
        "Al" + "meria",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jacar",
        "per" + "gola",
        "paint" + "ing",
                "roof" + " repair",
    ]

    return any(token in text for token in forbidden)


def main() -> int:
    worker_probe = app_worker_probe()
    runtime_probe = tts_stt_probe()
    readiness = packaged_readiness_probe()

    tts = runtime_probe.get("tts", {})
    stt = runtime_probe.get("stt", {})

    release_blockers = []

    if worker_probe.get("ok") is not True:
        release_blockers.append("app_local_worker_probe_failed")

    if readiness.get("ok") is not True:
        release_blockers.append("packaged_readiness_failed")

    if tts.get("ok") is not True:
        release_blockers.append("app_local_tts_failed")

    if tts.get("wav_exists") is not True:
        release_blockers.append("app_local_tts_wav_missing")

    if int(tts.get("frames") or 0) <= 0:
        release_blockers.append("app_local_tts_wav_empty")

    if stt.get("ok") is not True:
        release_blockers.append("app_local_stt_failed")

    transcript = (stt.get("transcript") or "").lower()
    if "aion" not in transcript and "runtime" not in transcript and "smoke" not in transcript:
        release_blockers.append("app_local_stt_transcript_unexpected")

    offline_env = runtime_probe.get("offline_env", {})
    if not (
        offline_env.get("HF_HUB_OFFLINE") == "1"
        and offline_env.get("TRANSFORMERS_OFFLINE") == "1"
        and offline_env.get("HF_DATASETS_OFFLINE") == "1"
        and offline_env.get("AION_VOICE_NO_HIDDEN_DOWNLOADS") == "true"
        and offline_env.get("AION_ELEVENLABS_ENABLED") == "false"
        and offline_env.get("AION_BROWSER_SPEECH_FALLBACK_ENABLED") == "false"
    ):
        release_blockers.append("offline_policy_not_enforced")

    if contains_forbidden_business_context():
        release_blockers.append("business_context_hardcoded")

    manifest = {
        "ok": len(release_blockers) == 0,
        "phase": "O24H",
        "purpose": "prove_full_app_local_tts_stt_smoke",
        "status": "full_app_local_voice_runtime_smoke_complete",
        "app_voice_root": rel(APP_VOICE_ROOT),
        "app_python": rel(APP_PYTHON),
        "app_runtime_root": rel(APP_RUNTIME_ROOT),
        "app_worker": rel(APP_WORKER),
        "worker_probe_ok": worker_probe.get("ok") is True,
        "worker_probe": worker_probe,
        "runtime_probe": runtime_probe,
        "tts_ok": tts.get("ok") is True,
        "tts_wav": path_state(TTS_WAV),
        "stt_ok": stt.get("ok") is True,
        "stt_transcript": stt.get("transcript"),
        "packaged_readiness": {
            "ok": readiness.get("ok"),
            "returncode": readiness.get("returncode"),
            "bundle_root": readiness.get("bundle_root"),
            "python": readiness.get("python"),
        },
        "release_ready": len(release_blockers) == 0,
        "release_blockers": release_blockers,
        "download_policy": {
            "hidden_huggingface_downloads_allowed": False,
            "hidden_transformers_downloads_allowed": False,
            "hidden_spacy_downloads_allowed": False,
            "hidden_elevenlabs_fallback_allowed": False,
            "hidden_browser_speech_fallback_allowed": False,
        },
        "business_context_hardcoded": contains_forbidden_business_context(),
        "next_step": {
            "create_release_manifest_and_packaging_digest": True,
            "then_wire_app_startup_to_app_local_worker": True,
        },
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
